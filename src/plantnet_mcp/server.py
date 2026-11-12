from __future__ import annotations

import argparse
import sys
from typing import Any

from mcp.server import MCPServer

from . import __version__
from .client import PlantNetClient, PlantNetError

DEFAULT_INSTRUCTIONS = """
Pl@ntNet MCP Server: Automated botanical identification powered by deep learning.

Key Best Practices:
1. Call `identify_plant_image` with an image URL or local photo file path.
2. Specify organ type: 'flower', 'leaf', 'fruit', 'bark', 'habit', or 'other'.
3. For multi-photo submissions, use `identify_plant_batch` to combine views.
4. Call `list_supported_projects` to target regional floras (e.g. 'weurope', 'namerica').
5. Output includes confidence scores, accepted names, and cross-references for GBIF and POWO.
""".strip()


def _format_plant_summary(result: dict[str, Any]) -> str:
    best = result.get("best_match")
    if not best:
        return "No plant species matches found."
    score_pct = round(best.get("score", 0.0) * 100, 1)
    common = ", ".join(best.get("common_names", [])[:3]) or "No common name recorded"
    lines = [
        f"Top Match: {best.get('scientific_name')} ({score_pct}% confidence)",
        f"Family: {best.get('family')} | Genus: {best.get('genus')}",
        f"Common Names: {common}",
    ]
    if best.get("gbif_id"):
        lines.append(f"GBIF ID: {best.get('gbif_id')} | POWO ID: {best.get('powo_id', 'N/A')}")
    return "\n".join(lines)


def create_server(client: PlantNetClient | None = None) -> MCPServer:
    """Create and configure the Pl@ntNet MCPServer instance."""
    api = client or PlantNetClient()

    server = MCPServer(
        "plantnet",
        version=__version__,
        instructions=DEFAULT_INSTRUCTIONS,
    )

    @server.tool()
    def identify_plant_image(
        image_source: str,
        organ: str = "flower",
        project: str = "k-world-flora",
    ) -> dict[str, Any]:
        """Identify plant species from an image URL or local file path."""
        try:
            res = api.identify_plant_image(image_source=image_source, organ=organ, project=project)
            res["summary"] = _format_plant_summary(res)
            return res
        except PlantNetError as exc:
            return {
                "error": str(exc),
                "results": [],
                "summary": f"Plant identification failed: {exc}",
            }

    @server.tool()
    def identify_plant_batch(
        images: list[str],
        organs: list[str] | None = None,
        project: str = "k-world-flora",
    ) -> dict[str, Any]:
        """Identify plant species from multiple images (up to 5 URLs or files) with organ tags."""
        try:
            res = api.identify_plant_batch(images=images, organs=organs, project=project)
            res["summary"] = _format_plant_summary(res)
            return res
        except PlantNetError as exc:
            return {
                "error": str(exc),
                "results": [],
                "summary": f"Batch identification failed: {exc}",
            }

    @server.tool()
    def list_supported_projects() -> dict[str, Any]:
        """List available geographic and thematic flora identification projects."""
        projects = api.list_supported_projects()
        lines = [f"- {code}: {desc}" for code, desc in projects.items()]
        summary = "\n".join(lines)
        return {"projects": projects, "summary": summary}

    return server


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="plantnet-mcp",
        description="Model Context Protocol (MCP) server for Pl@ntNet plant identification",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport protocol to use (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind for SSE transport (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind for SSE transport (default: 8000)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    server = create_server()
    if args.transport == "stdio":
        server.run(transport="stdio")
    else:
        server.run(transport="sse", host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
