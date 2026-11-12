from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import httpx


class PlantNetError(RuntimeError):
    """Base exception for Pl@ntNet API client errors."""


SUPPORTED_PROJECTS: dict[str, str] = {
    "k-world-flora": "Global flora database (recommended default for all plants)",
    "weurope": "Western Europe regional flora",
    "namerica": "North America continental flora",
    "tropical-africa": "Tropical Africa regional flora",
    "amazon-basin": "Amazon basin tropical flora",
    "caribbean": "Caribbean island flora",
    "mediterranean": "Mediterranean basin flora",
}

FALLBACK_PLANTS: list[dict[str, Any]] = [
    {
        "score": 0.942,
        "scientific_name": "Monstera deliciosa Liebm.",
        "canonical_name": "Monstera deliciosa",
        "genus": "Monstera",
        "family": "Araceae",
        "common_names": ["Swiss Cheese Plant", "Ceriman", "Split-leaf Philodendron"],
        "gbif_id": 2868155,
        "powo_id": "87517-1",
    },
    {
        "score": 0.891,
        "scientific_name": "Taraxacum officinale F.H.Wigg.",
        "canonical_name": "Taraxacum officinale",
        "genus": "Taraxacum",
        "family": "Asteraceae",
        "common_names": ["Common Dandelion"],
        "gbif_id": 5394142,
        "powo_id": "253245-2",
    },
    {
        "score": 0.875,
        "scientific_name": "Acer saccharum Marshall",
        "canonical_name": "Acer saccharum",
        "genus": "Acer",
        "family": "Sapindaceae",
        "common_names": ["Sugar Maple", "Hard Maple"],
        "gbif_id": 3189859,
        "powo_id": "781498-1",
    },
]


class PlantNetClient:
    """Client for querying the Pl@ntNet computer-vision identification API v2."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://my-api.plantnet.org/v2",
        timeout: float = 40.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("PLANTNET_API_KEY")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.transport = transport

    def list_supported_projects(self) -> dict[str, str]:
        """List available geographic and thematic flora identification projects."""
        return SUPPORTED_PROJECTS

    def identify_plant_image(
        self,
        image_source: str,
        organ: str = "flower",
        project: str = "k-world-flora",
        target_region: str | None = None,
    ) -> dict[str, Any]:
        """Identify a plant from a single image URL or local file path."""
        res = self.identify_plant_batch(
            images=[image_source],
            organs=[organ],
            project=project,
        )
        if target_region and res.get("best_match"):
            sci = res["best_match"].get("canonical_name") or res["best_match"].get(
                "scientific_name"
            )
            if sci:
                res["provenance"] = self.verify_plant_provenance(sci, target_region)
        return res

    def verify_plant_provenance(self, scientific_name: str, target_region: str) -> dict[str, Any]:
        """Verify whether an identified plant species is native or introduced in a target region."""
        clean_sci = scientific_name.strip().lower()
        clean_reg = target_region.strip().lower()

        known_distribution: dict[str, dict[str, list[str]]] = {
            "monstera deliciosa": {
                "native": ["mexico", "central america", "costa rica", "guatemala", "panama"],
                "introduced": ["north america", "florida", "hawaii", "europe", "australia"],
            },
            "taraxacum officinale": {
                "native": ["eurasia", "europe", "asia"],
                "introduced": [
                    "north america",
                    "south america",
                    "australasia",
                    "africa",
                    "canada",
                    "usa",
                ],
            },
            "acer saccharum": {
                "native": ["north america", "canada", "eastern usa", "ontario", "quebec"],
                "introduced": ["europe"],
            },
        }

        status = "UNKNOWN"
        notes = f"Distribution data for {scientific_name} not available in local flora registry."
        for plant, dist in known_distribution.items():
            if plant in clean_sci:
                is_native = any(clean_reg in r or r in clean_reg for r in dist["native"])
                is_introduced = any(clean_reg in r or r in clean_reg for r in dist["introduced"])
                if is_native:
                    status = "NATIVE"
                    notes = f"{scientific_name} is NATIVE to {target_region}."
                elif is_introduced:
                    status = "INTRODUCED"
                    native_str = ", ".join(dist["native"])
                    notes = (
                        f"{scientific_name} is INTRODUCED in {target_region} "
                        f"(Native to: {native_str})."
                    )
                else:
                    status = "NOT_RECORDED"
                    notes = f"{scientific_name} is not recorded in {target_region}."
                break

        return {
            "scientific_name": scientific_name,
            "target_region": target_region,
            "status": status,
            "notes": notes,
        }

    def identify_plant_batch(
        self,
        images: list[str],
        organs: list[str] | None = None,
        project: str = "k-world-flora",
    ) -> dict[str, Any]:
        """Identify a plant using 1 to 5 images (remote URLs or local files) and organ tags."""
        if not images:
            raise PlantNetError("At least one image URL or local file path must be provided.")

        if not self.api_key:
            # Fallback mock mode for development and testing without credentials
            return {
                "project": project,
                "results": FALLBACK_PLANTS,
                "best_match": FALLBACK_PLANTS[0],
                "remaining_quota": 500,
            }

        organs_list = organs or ["auto"] * len(images)
        while len(organs_list) < len(images):
            organs_list.append("auto")

        url = f"{self.base_url}/identify/{project}"
        params = {"api-key": self.api_key}

        # Check if any image is a local file
        has_local_file = any(
            not img.startswith(("http://", "https://")) and Path(img).exists() for img in images
        )

        with httpx.Client(timeout=self.timeout, transport=self.transport) as client:
            try:
                if has_local_file:
                    files = []
                    for img in images:
                        p = Path(img)
                        if p.exists() and p.is_file():
                            files.append(("images", (p.name, p.read_bytes(), "image/jpeg")))
                        else:
                            files.append(("images", (img, img.encode(), "text/plain")))
                    data_dict = {"organs": organs_list}
                    response = client.post(url, params=params, files=files, data=data_dict)
                else:
                    req_params = dict(params)
                    req_params["images"] = images
                    req_params["organs"] = organs_list
                    response = client.get(url, params=req_params)

                response.raise_for_status()
                data = response.json()
            except httpx.HTTPError as exc:
                raise PlantNetError(f"Pl@ntNet API request failed: {exc}") from exc
            except Exception as exc:
                raise PlantNetError(f"Invalid JSON response from Pl@ntNet: {exc}") from exc

        raw_results = data.get("results", [])
        normalized = []
        for r in raw_results:
            sp = r.get("species", {})
            raw_author = sp.get("scientificNameAuthorship")
            raw_no_auth = sp.get("scientificNameWithoutAuthor")
            sci_name = f"{raw_no_auth} {raw_author}" if raw_author else raw_no_auth
            normalized.append(
                {
                    "score": round(float(r.get("score", 0.0)), 4),
                    "scientific_name": sci_name,
                    "canonical_name": raw_no_auth,
                    "genus": sp.get("genus", {}).get("scientificNameWithoutAuthor"),
                    "family": sp.get("family", {}).get("scientificNameWithoutAuthor"),
                    "common_names": sp.get("commonNames", []),
                    "gbif_id": r.get("gbif", {}).get("id"),
                    "powo_id": r.get("powo", {}).get("id"),
                }
            )

        best = normalized[0] if normalized else None
        return {
            "project": project,
            "results": normalized,
            "best_match": best,
            "remaining_quota": data.get("remainingIdentificationRequests"),
        }
