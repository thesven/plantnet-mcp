# plantnet-mcp

[![CI](https://github.com/thesven/plantnet-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/thesven/plantnet-mcp/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A computer-vision botanical identification **Model Context Protocol (MCP)** server powered by the [Pl@ntNet API v2](https://my-api.plantnet.org/).

Enables AI agents to identify plant species from photographs (both remote URLs and local image file paths), with multi-organ support (flower, leaf, fruit, bark), regional floras, and cross-linking to GBIF and Kew's Plants of the World Online (POWO).

---

## Key Features

- **Local & Remote Image Ingestion**: Supports public image URLs as well as direct local image files on disk via multipart upload.
- **Botanical Provenance & Native Range Verification**: Checks whether an identified species is native, introduced, or exotic in the user's geographic region.
- **Multi-Organ Identification**: Submit multiple complementary views of the same plant (e.g. leaf + flower + habit) to maximize identification accuracy.
- **Regional Flora Scope**: Target specific continental floras (`weurope`, `namerica`, `tropical-africa`, `mediterranean`, `caribbean`) or use the default `k-world-flora`.
- **Cross-Platform Botanical Linking**: Returns matched species with accepted scientific names, common names, confidence scores, and direct identifiers for GBIF and POWO.
- **Graceful Fallback Mode**: Functions in reference demo mode when an API key is not present, making it easy to test and evaluate locally.

---

## Available Tools

| Tool | Description |
| :--- | :--- |
| `identify_plant_image` | Identify a plant from a single image URL or local photo file path with optional provenance check. |
| `identify_plant_batch` | Identify a plant using 1 to 5 images and organ tags (flower, leaf, fruit, bark, habit). |
| `verify_plant_provenance` | Verify whether an identified plant species is native or introduced in a target region. |
| `list_supported_projects` | List available geographic and thematic flora identification projects. |

---

## Installation & Usage

### Running with `uvx` (Recommended)

```bash
# With Pl@ntNet API Key
PLANTNET_API_KEY=your_key_here uvx --from git+https://github.com/thesven/plantnet-mcp.git plantnet-mcp

# Or in offline reference mode
uvx --from git+https://github.com/thesven/plantnet-mcp.git plantnet-mcp
```

### Claude Desktop Configuration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "plantnet": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/thesven/plantnet-mcp.git", "plantnet-mcp"],
      "env": {
        "PLANTNET_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

---

## Development & Quality Gate

```bash
# Run code formatting check
uv run ruff format --check src tests scripts

# Run linting
uv run ruff check src tests scripts

# Run test suite with strict coverage floor (>90%)
uv run pytest --cov=plantnet_mcp --cov-branch --cov-report=term-missing

# Build wheel and sdist
uv build

# Run package distribution check & smoke test
uv run python scripts/check_dist.py
uv run python scripts/smoke.py
```

## License

MIT License. See [LICENSE](LICENSE) for details.
