from __future__ import annotations

import tempfile
from pathlib import Path

import httpx
import pytest

from plantnet_mcp.client import PlantNetClient, PlantNetError


def test_client_init() -> None:
    client = PlantNetClient(api_key="test-key", base_url="https://my-api.plantnet.org/v2/")
    assert client.base_url == "https://my-api.plantnet.org/v2"
    assert client.api_key == "test-key"
    projects = client.list_supported_projects()
    assert "k-world-flora" in projects


def test_fallback_mode_no_api_key() -> None:
    client = PlantNetClient(api_key=None)
    res = client.identify_plant_image("https://example.com/flower.jpg", organ="flower")
    assert res["project"] == "k-world-flora"
    assert len(res["results"]) >= 1
    assert res["best_match"]["canonical_name"] == "Monstera deliciosa"
    assert res["best_match"]["gbif_id"] == 2868155


def test_empty_images_raises() -> None:
    client = PlantNetClient(api_key="key")
    with pytest.raises(PlantNetError, match="At least one image"):
        client.identify_plant_batch([])


def test_identify_plant_remote_urls_api() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/identify/k-world-flora"
        assert request.url.params["api-key"] == "real-key"
        return httpx.Response(
            200,
            json={
                "remainingIdentificationRequests": 450,
                "results": [
                    {
                        "score": 0.9123,
                        "species": {
                            "scientificNameWithoutAuthor": "Taraxacum officinale",
                            "scientificNameAuthorship": "F.H.Wigg.",
                            "genus": {"scientificNameWithoutAuthor": "Taraxacum"},
                            "family": {"scientificNameWithoutAuthor": "Asteraceae"},
                            "commonNames": ["Dandelion"],
                        },
                        "gbif": {"id": 12345},
                        "powo": {"id": "67890"},
                    }
                ],
            },
        )

    transport = httpx.MockTransport(handler)
    client = PlantNetClient(api_key="real-key", transport=transport)
    res = client.identify_plant_image("https://example.com/dandelion.jpg", organ="flower")
    assert res["remaining_quota"] == 450
    assert res["best_match"]["canonical_name"] == "Taraxacum officinale"
    assert res["best_match"]["score"] == 0.9123


def test_identify_plant_local_files_api() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        return httpx.Response(
            200,
            json={
                "remainingIdentificationRequests": 449,
                "results": [
                    {
                        "score": 0.88,
                        "species": {
                            "scientificNameWithoutAuthor": "Acer saccharum",
                            "genus": {"scientificNameWithoutAuthor": "Acer"},
                            "family": {"scientificNameWithoutAuthor": "Sapindaceae"},
                        },
                    }
                ],
            },
        )

    transport = httpx.MockTransport(handler)
    client = PlantNetClient(api_key="real-key", transport=transport)

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        f.write(b"fake-image-bytes")
        f.flush()
        local_path = f.name

    try:
        res = client.identify_plant_batch([local_path], organs=["leaf"])
        assert res["best_match"]["canonical_name"] == "Acer saccharum"
    finally:
        Path(local_path).unlink(missing_ok=True)


def test_error_handling() -> None:
    def handler_500(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Pl@ntNet Server Down")

    client = PlantNetClient(api_key="key", transport=httpx.MockTransport(handler_500))
    with pytest.raises(PlantNetError, match="Pl@ntNet API request failed"):
        client.identify_plant_image("https://example.com/test.jpg")

    def handler_bad_json(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"invalid-json{")

    client2 = PlantNetClient(api_key="key", transport=httpx.MockTransport(handler_bad_json))
    with pytest.raises(PlantNetError, match="Invalid JSON"):
        client2.identify_plant_image("https://example.com/test.jpg")
