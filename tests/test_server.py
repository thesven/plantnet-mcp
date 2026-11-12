from __future__ import annotations

import httpx
import pytest

from plantnet_mcp.client import PlantNetClient
from plantnet_mcp.server import create_server


@pytest.fixture
def mock_client() -> PlantNetClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if "/species" in request.url.path:
            return httpx.Response(
                200,
                json=[
                    {
                        "scientificNameWithoutAuthor": "Monstera deliciosa",
                        "scientificNameAuthorship": "Liebm.",
                        "family": {"scientificNameWithoutAuthor": "Araceae"},
                        "commonNames": ["Swiss Cheese Plant"],
                        "gbifId": 2868155,
                        "powoId": "87517-1",
                    }
                ],
            )
        return httpx.Response(
            200,
            json={
                "remainingIdentificationRequests": 500,
                "results": [
                    {
                        "score": 0.95,
                        "species": {
                            "scientificNameWithoutAuthor": "Monstera deliciosa",
                            "genus": {"scientificNameWithoutAuthor": "Monstera"},
                            "family": {"scientificNameWithoutAuthor": "Araceae"},
                            "commonNames": ["Swiss Cheese Plant"],
                        },
                        "gbif": {"id": 2868155},
                        "powo": {"id": "87517-1"},
                    }
                ],
            },
        )

    return PlantNetClient(api_key="mock-key", transport=httpx.MockTransport(handler))


@pytest.fixture
def failing_client() -> PlantNetClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Pl@ntNet Server Error")

    return PlantNetClient(api_key="mock-key", transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_server_tools(mock_client: PlantNetClient) -> None:
    server = create_server(mock_client)

    tools = await server.list_tools()
    tool_names = {t.name for t in tools}
    assert "identify_plant_image" in tool_names
    assert "identify_plant_batch" in tool_names
    assert "list_supported_projects" in tool_names
    assert "verify_plant_provenance" in tool_names
    assert "get_supported_organs" in tool_names
    assert "search_project_species" in tool_names

    res = await server.call_tool(
        "identify_plant_image",
        {
            "image_source": "https://example.com/leaf.jpg",
            "organ": "leaf",
            "target_region": "Mexico",
        },
    )
    assert "Monstera deliciosa" in res.content[0].text
    assert "GBIF ID" in res.content[0].text
    assert "Provenance" in res.content[0].text

    res = await server.call_tool(
        "verify_plant_provenance",
        {"scientific_name": "Taraxacum officinale", "target_region": "North America"},
    )
    assert "INTRODUCED" in res.content[0].text

    res = await server.call_tool(
        "identify_plant_batch", {"images": ["https://example.com/leaf.jpg"]}
    )
    assert "Monstera deliciosa" in res.content[0].text

    res = await server.call_tool("list_supported_projects", {})
    assert "k-world-flora" in res.content[0].text

    res = await server.call_tool("get_supported_organs", {})
    assert "flower" in res.content[0].text
    assert "leaf" in res.content[0].text

    res = await server.call_tool("search_project_species", {"query": "Monstera"})
    assert "Monstera deliciosa" in res.content[0].text


@pytest.mark.asyncio
async def test_server_tool_errors(failing_client: PlantNetClient) -> None:
    server = create_server(failing_client)

    res = await server.call_tool(
        "identify_plant_image", {"image_source": "https://example.com/bad.jpg"}
    )
    assert "failed" in res.content[0].text

    res = await server.call_tool(
        "identify_plant_batch", {"images": ["https://example.com/bad.jpg"]}
    )
    assert "failed" in res.content[0].text

    res = await server.call_tool("search_project_species", {"query": "   "})
    assert "failed" in res.content[0].text
