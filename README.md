# USPTO MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server that exposes the U.S. Patent and Trademark Office (USPTO) public APIs as tools for AI agents. Search patents and applications, check trademark status, browse PTAB proceedings, and query USPTO bulk datasets — all over the MCP stdio transport.

- **20 tools** covering the USPTO Open Data Portal (ODP), TSDR, and dataset APIs
- Runs as a **Docker container** over stdio, or directly with Python
- Ships with a **Docker MCP Gateway** catalog definition ([`catalog.yaml`](catalog.yaml))

## Tools

| Area | Tools |
|------|-------|
| **Patents** | `patent_search`, `patent_lookup`, `patent_documents`, `patent_application_detail`, `patent_status_codes`, `patent_appeals_search`, `patent_interferences_search`, `list_bulk_data_products` |
| **PTAB** | `ptab_search`, `ptab_detail`, `ptab_trial_decisions_search`, `ptab_trial_documents_search`, `petition_decisions_search` |
| **Trademarks** | `trademark_status`, `trademark_multi_status`, `trademark_documents`, `trademark_last_update` |
| **Datasets** | `list_datasets`, `list_dataset_fields`, `search_dataset` |

## Backends

| Source | Base URL | Used for |
|--------|----------|----------|
| **ODP** (primary) | `https://api.uspto.gov` | Patents, applications, PTAB, appeals, interferences, petitions, datasets |
| **TSDR** | `https://tsdrapi.uspto.gov` | Trademark status and documents |
| **PatentsView** (optional) | `https://search.patentsview.org` | Supplementary granted-patent enrichment — only used if `PATENTSVIEW_API_KEY` is set. Note: PatentsView has suspended issuing new API keys. |

## Requirements

- Python 3.12+
- `mcp[cli]>=1.0.0`, `httpx>=0.27.0` (see [`requirements.txt`](requirements.txt))
- A USPTO API key from [developer.uspto.gov](https://developer.uspto.gov) — passed via the `USPTO_API_KEY` environment variable and sent as the `x-api-key` header (ODP) / `USPTO-API-KEY` header (TSDR).

## Running

### With Docker (recommended)

```bash
docker build -t uspto-mcp-server:latest .
```

The container communicates over **stdio**, so it's launched by your MCP client rather than run standalone. Example MCP client config:

```json
{
  "mcpServers": {
    "uspto": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "-e", "USPTO_API_KEY", "uspto-mcp-server:latest"],
      "env": { "USPTO_API_KEY": "your_api_key_here" }
    }
  }
}
```

### With Python directly

```bash
pip install -r requirements.txt
export USPTO_API_KEY=your_api_key_here   # PowerShell: $env:USPTO_API_KEY="..."
python server.py
```

### With the Docker MCP Gateway

[`catalog.yaml`](catalog.yaml) defines this server for the Docker MCP Gateway catalog, including the secret → environment-variable mapping. Provide `uspto.api_key` (and optionally `patentsview.api_key`) as Docker MCP secrets — **never hard-code credentials in the catalog.**

## Documentation

- [`TECHNICAL_HANDOFF.md`](TECHNICAL_HANDOFF.md) — full architecture, tool-to-endpoint inventory, ODP query DSL, retry logic, deployment, and troubleshooting.
- [`resources/`](resources/) — USPTO API reference documents (ODP query spec, PEDS→ODP mapping, field schema). See [`resources/REFERENCES.md`](resources/REFERENCES.md).

## License

MIT
