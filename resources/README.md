# USPTO MCP Server — Reference Documents

These documents are the authoritative source for fixing and improving the MCP server.

## Files

| File | Description |
|------|-------------|
| `USPTO_ODP_API_Reference.md` | **Start here.** Complete API reference compiled from all sources below. Endpoints, parameters, query syntax, field names, examples. |
| `patent_data_schema.json` | Full 274-field JSON schema for patent data responses. Use for understanding response structure and valid field names. |
| `ODP_API_Query_Spec.pdf` | Official USPTO "Simplified Query Syntax" document. Covers GET/POST search, q parameter DSL, filters, rangeFilters, sort, fields, pagination, facets. |
| `PEDS_to_ODP_Mapping.pdf` | Official PEDS→ODP migration mapping. Shows old PEDS endpoints → new ODP equivalents. Key source for endpoint URLs and document download flow. |
| `USPTO_API_Key_Transcript.pdf` | How to obtain an API key (ID.me + USPTO account required). |

## Critical Fix Needed

The current `server.py` uses `https://data.uspto.gov` as the base URL. USPTO now returns 400:
> "Please use the api.uspto.gov endpoint as this endpoint is intended for the web UI use only."

### What must change:
1. **Base URL**: `https://data.uspto.gov` → `https://api.uspto.gov`
2. **Auth header**: `X-API-KEY: <key>` (read from env `USPTO_API_KEY`)
3. **Search param**: Already fixed to `q` (correct)
4. **Field-specific queries use qualified names**: e.g. `applicationMetaData.patentNumber:9524132` (not just `patentNumber:9524132`)
5. **POST search** should be added — more powerful than GET (supports filters, rangeFilters, facets as structured JSON)
6. **Document download** is two-step: first get metadata at `/api/v1/patent/applications/{appNum}/documents`, then use the `downloadUrl` from each document's `downloadOptionBag`

### Current issue:
The API key (`qwr...qw` stored in Docker MCP secret `uspto.api_key`) returns 403 Forbidden on `api.uspto.gov`. Either:
- The key needs activation on the new gateway
- The endpoint path is wrong
- Test via Swagger UI at `https://data.uspto.gov/swagger/index.html` (click Authorize, enter key, try a search)
