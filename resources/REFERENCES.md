# USPTO MCP Server — Reference Documents

These documents are the authoritative source for the USPTO APIs this server wraps.
See the [root README](../README.md) for how to run the server, and
[`TECHNICAL_HANDOFF.md`](../TECHNICAL_HANDOFF.md) for architecture and implementation detail.

> **Reference material compiled March 15, 2026.** USPTO APIs evolve — verify currency
> against the [official USPTO documentation](https://data.uspto.gov/apis/getting-started)
> before relying on any time-sensitive detail.

## Files

| File | Description |
|------|-------------|
| `USPTO_ODP_API_Reference.md` | **Start here.** Complete API reference compiled from all sources below. Endpoints, parameters, query syntax, field names, examples. |
| `patent_data_schema.json` | Full 274-field JSON schema for patent data responses. Use for understanding response structure and valid field names. |
| `ODP_API_Query_Spec.pdf` | Official USPTO "Simplified Query Syntax" document. Covers GET/POST search, q parameter DSL, filters, rangeFilters, sort, fields, pagination, facets. |
| `PEDS_to_ODP_Mapping.pdf` | Official PEDS→ODP migration mapping. Shows old PEDS endpoints → new ODP equivalents. Key source for endpoint URLs and document download flow. |

## Key API notes

- **Base URL** is `https://api.uspto.gov` (the `data.uspto.gov` host is for the web UI only and returns 400 for programmatic calls).
- **Auth** uses the `x-api-key` header, read from the `USPTO_API_KEY` environment variable.
- **Field-specific queries use fully-qualified names**, e.g. `applicationMetaData.patentNumber:10467553`.
- **POST search** (`/search`) supports structured `filters`, `rangeFilters`, and `facets`; prefer it over GET for anything beyond simple keyword queries.
- **Document download is two-step**: get metadata at `/api/v1/patent/applications/{appNum}/documents`, then follow the `downloadUrl` in each document's `downloadOptionBag`.
