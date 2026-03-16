# USPTO MCP Server — Technical Handoff Document

> **Last updated:** 2026-03-16
> **Author:** AI-assisted (Claude) with human review
> **Repository:** `anaranillc/uspto-mcp-server`

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [API Backends](#3-api-backends)
4. [Authentication & API Keys](#4-authentication--api-keys)
5. [Tool Inventory (20 Tools → 48 Endpoints)](#5-tool-inventory)
6. [ODP Query DSL Reference](#6-odp-query-dsl-reference)
7. [POST Search Body Format](#7-post-search-body-format)
8. [Field Name System](#8-field-name-system)
9. [HTTP Client & Retry Logic](#9-http-client--retry-logic)
10. [Docker Deployment](#10-docker-deployment)
11. [Docker MCP Gateway Integration](#11-docker-mcp-gateway-integration)
12. [Edge Cases & Gotchas](#12-edge-cases--gotchas)
13. [Troubleshooting Playbook](#13-troubleshooting-playbook)
14. [Rebuilding from Scratch](#14-rebuilding-from-scratch)
15. [File Inventory](#15-file-inventory)
16. [Known Issues & Future Work](#16-known-issues--future-work)
17. [Reference Links](#17-reference-links)

---

## 1. Project Overview

This is a **Model Context Protocol (MCP) server** that exposes the US Patent and Trademark Office (USPTO) public APIs as tools consumable by AI agents (Claude, GPT, etc.) via the MCP standard.

**What it does:**
- Provides 20 MCP tools that cover all 48 ODP API endpoints
- Searches patents, patent applications, PTAB proceedings, appeals, interferences, petition decisions, trademark status, and USPTO bulk datasets
- Runs as a Docker container communicating over **stdio** (not HTTP)
- Designed for the Docker MCP Gateway catalog system

**Stack:**
- Python 3.12 (single-file server: `server.py`, ~1250 lines)
- `mcp[cli]` (FastMCP framework) for MCP protocol handling
- `httpx` for async HTTP with retry
- Docker (python:3.12-slim base image)

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────┐
│                    AI Agent (Claude, etc.)           │
│                          │                           │
│                     MCP Protocol                     │
│                      (stdio)                         │
└──────────────────────────┬──────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────┐
│              USPTO MCP Server (server.py)            │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ 20 Tools │  │ Headers  │  │ HTTP Client Pool │  │
│  │ (FastMCP)│  │ Builders │  │ (httpx + retry)  │  │
│  └──────────┘  └──────────┘  └──────────────────┘  │
│                                                      │
│  ┌─────────────────┐  ┌────────────────────────┐    │
│  │ Field Name      │  │ PatentsView Translator │    │
│  │ Expander        │  │ (ODP→PV query mapping) │    │
│  └─────────────────┘  └────────────────────────┘    │
└──────────────────────────┬──────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
┌───────────────┐ ┌───────────────┐ ┌──────────────┐
│ api.uspto.gov │ │tsdrapi.uspto  │ │developer.    │
│ (ODP v2)      │ │.gov (TSDR)    │ │uspto.gov     │
│               │ │               │ │(DS-API)      │
│ POST/GET JSON │ │ GET JSON      │ │ POST form    │
│ x-api-key     │ │ USPTO-API-KEY │ │ No auth      │
└───────────────┘ └───────────────┘ └──────────────┘
        │
        ▼ (optional supplementary)
┌───────────────┐
│search.patents │
│view.org       │
│(PatentsView)  │
│ GET JSON      │
└───────────────┘
```

### Key Design Decisions

1. **Single-file architecture** — All logic in `server.py`. No modules, no ORM, no config files beyond env vars. This simplifies Docker builds and debugging.

2. **stdio transport** — MCP runs over stdin/stdout. All logging goes to stderr. This is critical — any stray `print()` to stdout will corrupt the MCP protocol.

3. **POST for searches, GET for lookups** — ODP v2 uses POST with JSON body for all search endpoints. Single-record lookups use GET with path parameters.

4. **PatentsView as supplementary** — When a PatentsView API key is available, `patent_search` and `patent_lookup` enrich ODP results with granted patent data from PatentsView. This is additive — if PatentsView fails, ODP results are still returned.

5. **Parameterized tools for endpoint families** — Instead of 48 individual tools, we use parameterized tools (e.g., `patent_application_detail` with a `section` parameter covers 9 GET endpoints, `ptab_detail` with `resource_type` covers 10 GET endpoints).

---

## 3. API Backends

### 3.1 ODP v2 (Primary — Patent Data)

| Property | Value |
|----------|-------|
| Base URL | `https://api.uspto.gov` |
| Auth header | `x-api-key: <key>` (lowercase) |
| Content-Type | `application/json` |
| Search method | POST with JSON body |
| Lookup method | GET with path parameters |
| Rate limit | Not documented; use exponential backoff |
| WAF | AWS WAF — blocks requests without proper headers |

**CRITICAL HISTORY:** Before March 2026, the API was at `https://data.uspto.gov`. USPTO split it:
- `data.uspto.gov` → **web UI only** (returns 400 for programmatic requests with message "Please use the api.uspto.gov endpoint")
- `api.uspto.gov` → **programmatic API** (requires `x-api-key` header)

### 3.2 TSDR (Trademark Status & Document Retrieval)

| Property | Value |
|----------|-------|
| Base URL | `https://tsdrapi.uspto.gov` |
| Auth header | `USPTO-API-KEY: <key>` (note: different header name!) |
| Method | GET with query params |
| Rate limit | 60 requests/minute; 4 req/min for PDF/ZIP |
| No CORS | Server-to-server only |

### 3.3 DS-API (Developer Datasets)

| Property | Value |
|----------|-------|
| Base URL | `https://developer.uspto.gov/ds-api` |
| Auth | None required |
| Search method | POST with `application/x-www-form-urlencoded` body |
| Query syntax | Lucene |
| Datasets | `oa_citations`, `cancer_moonshot`, `mcf`, etc. |

### 3.4 PatentsView (Supplementary — Granted Patents)

| Property | Value |
|----------|-------|
| Base URL | `https://search.patentsview.org` |
| Auth header | `X-Api-Key: <key>` (note: different casing!) |
| Method | GET with query params |
| Status | **New key grants suspended** as of early 2026 |
| Query format | JSON query object (different from ODP DSL) |

---

## 4. Authentication & API Keys

### Environment Variables

| Variable | Required | Used By | Notes |
|----------|----------|---------|-------|
| `USPTO_API_KEY` | Yes | ODP, TSDR | Single key works for both but **different header names** |
| `PATENTSVIEW_API_KEY` | No | PatentsView | Supplementary; new grants suspended |

### How to Obtain a USPTO API Key

1. Create account at https://account.uspto.gov
2. Complete ID.me identity verification
3. Navigate to "My ODP" page at https://data.uspto.gov
4. Generate/view your API key
5. Alternatively check https://account.uspto.gov/api-manager/

### Header Differences (CRITICAL)

```python
# ODP (api.uspto.gov) — lowercase x-api-key
headers["x-api-key"] = API_KEY

# TSDR (tsdrapi.uspto.gov) — uppercase USPTO-API-KEY
headers["USPTO-API-KEY"] = API_KEY

# PatentsView (search.patentsview.org) — mixed case X-Api-Key
headers["X-Api-Key"] = API_KEY
```

HTTP headers are case-insensitive per RFC 7230, but these specific casings are confirmed working. Some intermediary proxies or WAFs may be case-sensitive in practice.

---

## 5. Tool Inventory

### Tool → Endpoint Mapping

| # | Tool Name | Method | Endpoint(s) | API Backend |
|---|-----------|--------|-------------|-------------|
| 1 | `trademark_status` | GET | `/ts/cd/casestatus/{id}/info` | TSDR |
| 2 | `trademark_multi_status` | GET | `/ts/cd/caseMultiStatus/{type}` | TSDR |
| 3 | `trademark_documents` | GET | `/ts/cd/casedocs/{id}/info` | TSDR |
| 4 | `trademark_last_update` | GET | `/last-update/info.json` | TSDR |
| 5 | `list_datasets` | GET | `/ds-api/` | DS-API |
| 6 | `list_dataset_fields` | GET | `/ds-api/{dataset}/{ver}/fields` | DS-API |
| 7 | `search_dataset` | POST | `/ds-api/{dataset}/{ver}/records` | DS-API |
| 8 | `patent_search` | POST | `/api/v1/patent/applications/search` | ODP |
| 9 | `patent_lookup` | GET/POST | `/api/v1/patent/applications/{num}` (by app#) or POST search (by patent#) | ODP |
| 10 | `patent_documents` | GET | `/api/v1/patent/applications/{num}/documents` | ODP |
| 11 | `list_bulk_data_products` | GET | `/api/v1/datasets/products/search` | ODP |
| 12 | `ptab_search` | POST | `/api/v1/patent/trials/proceedings/search` | ODP |
| 13 | `petition_decisions_search` | POST | `/api/v1/petition/decisions/search` | ODP |
| 14 | `patent_appeals_search` | POST | `/api/v1/patent/appeals/decisions/search` | ODP |
| 15 | `patent_interferences_search` | POST | `/api/v1/patent/interferences/decisions/search` | ODP |
| 16 | `patent_application_detail` | GET | 9 endpoints (see below) | ODP |
| 17 | `patent_status_codes` | POST | `/api/v1/patent/status-codes` | ODP |
| 18 | `ptab_trial_decisions_search` | POST | `/api/v1/patent/trials/decisions/search` | ODP |
| 19 | `ptab_trial_documents_search` | POST | `/api/v1/patent/trials/documents/search` | ODP |
| 20 | `ptab_detail` | GET | 10 endpoints (see below) | ODP |

### Tool 16: `patent_application_detail` — Section Parameter

| `section` value | Endpoint |
|-----------------|----------|
| `""` (empty) | `GET /api/v1/patent/applications/{appNum}` |
| `"meta-data"` | `GET /api/v1/patent/applications/{appNum}/meta-data` |
| `"adjustment"` | `GET /api/v1/patent/applications/{appNum}/adjustment` |
| `"assignment"` | `GET /api/v1/patent/applications/{appNum}/assignment` |
| `"attorney"` | `GET /api/v1/patent/applications/{appNum}/attorney` |
| `"continuity"` | `GET /api/v1/patent/applications/{appNum}/continuity` |
| `"foreign-priority"` | `GET /api/v1/patent/applications/{appNum}/foreign-priority` |
| `"transactions"` | `GET /api/v1/patent/applications/{appNum}/transactions` |
| `"documents"` | `GET /api/v1/patent/applications/{appNum}/documents` |
| `"associated-documents"` | `GET /api/v1/patent/applications/{appNum}/associated-documents` |

### Tool 20: `ptab_detail` — Resource Type Parameter

| `resource_type` value | Endpoint |
|-----------------------|----------|
| `"proceeding"` | `GET /api/v1/patent/trials/proceedings/{trialNumber}` |
| `"decision"` | `GET /api/v1/patent/trials/decisions/{docId}` |
| `"document"` | `GET /api/v1/patent/trials/documents/{docId}` |
| `"appeal"` | `GET /api/v1/patent/appeals/decisions/{docId}` |
| `"appeal_by_number"` | `GET /api/v1/patent/appeals/{appealNumber}/decisions` |
| `"interference"` | `GET /api/v1/patent/interferences/decisions/{docId}` |
| `"interference_by_number"` | `GET /api/v1/patent/interferences/{interferenceNumber}/decisions` |
| `"trial_decisions"` | `GET /api/v1/patent/trials/{trialNumber}/decisions` |
| `"trial_documents"` | `GET /api/v1/patent/trials/{trialNumber}/documents` |
| `"petition"` | `GET /api/v1/patent/decisions/{petitionDecisionRecordId}` |

### Coverage: All 48 ODP Swagger Endpoints

The 48 endpoints from the official Swagger spec (`swagger.yaml`) map to the 20 tools above. The breakdown by Swagger tag:

- **Patent Search** (3 endpoints): POST search, GET search, GET download → Tool 8 (`patent_search`)
- **Patent Application Data** (10 endpoints): GET by app# + 9 sections → Tool 9 (`patent_lookup`), Tool 10 (`patent_documents`), Tool 16 (`patent_application_detail`)
- **Bulk DataSets** (2 endpoints): GET products/search, GET products/{id} → Tool 11 (`list_bulk_data_products`)
- **Petition Decision** (3 endpoints): POST search, GET by ID → Tool 13, Tool 20 (petition)
- **PTAB Trials:Proceedings** (4 endpoints): POST search, GET by trial#, GET decisions, GET documents → Tool 12, Tool 20 (proceeding, trial_decisions, trial_documents)
- **PTAB Trials:Decisions** (3 endpoints): POST search, GET by docId → Tool 18, Tool 20 (decision)
- **PTAB Trials:Documents** (3 endpoints): POST search, GET by docId → Tool 19, Tool 20 (document)
- **PTAB Appeals** (5 endpoints): POST search, GET by docId, GET by appeal# → Tool 14, Tool 20 (appeal, appeal_by_number)
- **PTAB Interferences** (5 endpoints): POST search, GET by docId, GET by interference# → Tool 15, Tool 20 (interference, interference_by_number)
- **Patent Status Codes** (1 endpoint): POST → Tool 17
- **GET search** (same endpoint as POST search): Covered by Tool 8 (we use POST which is more powerful)
- **Download search results**: `GET /api/v1/patent/applications/search/download` — not exposed as a tool (6MB limit, better handled by bulk data)

---

## 6. ODP Query DSL Reference

The `q` parameter in ODP search endpoints accepts a powerful query DSL. This is passed directly — the server does NOT parse or restructure it (beyond field name expansion).

### Syntax

| Pattern | Example | Notes |
|---------|---------|-------|
| Keywords | `artificial intelligence` | Free-text search |
| Field:Value | `applicationMetaData.patentNumber:9524132` | Field must be fully qualified |
| AND | `Utility AND Design` | Boolean AND |
| OR | `Small OR Micro` | Boolean OR |
| NOT | `"Patented Case" NOT Design` | Boolean NOT |
| Phrase | `"ink jet printer"` | Exact phrase match |
| Wildcard * | `Technolog*` | Prefix matching |
| Wildcard ? | `ANDERS?N` | Single character |
| Range | `filingDate:[2024-01-01 TO 2024-12-31]` | Inclusive range |
| Comparison | `applicationStatusDate:>=2024-02-20` | Greater/less than |
| Multi-value | `applicationTypeLabelName:(Design OR Plant)` | OR within field |

### Important: Field Names Must Be Fully Qualified

The API requires fully qualified dotted field names. For example:
- **Wrong:** `patentNumber:9524132`
- **Right:** `applicationMetaData.patentNumber:9524132`

The server includes `_expand_field_names()` that auto-expands common short names, but users/agents should prefer fully qualified names.

---

## 7. POST Search Body Format

All ODP search endpoints (`/search`) accept the same POST body structure:

```json
{
  "q": "applicationMetaData.inventionTitle:printer",
  "filters": [
    {
      "name": "applicationMetaData.applicationTypeCode",
      "value": ["UTL"]
    }
  ],
  "rangeFilters": [
    {
      "field": "applicationMetaData.grantDate",
      "valueFrom": "2020-01-01",
      "valueTo": "2024-12-31"
    }
  ],
  "sort": [
    {
      "field": "applicationMetaData.filingDate",
      "order": "Desc"
    }
  ],
  "pagination": {
    "offset": 0,
    "limit": 25
  }
}
```

### CRITICAL: Filter Format

```json
// CORRECT — uses "name" key, "value" is an array
{"name": "fieldName", "value": ["val1", "val2"]}

// WRONG — uses "field" key, "value" is a string
{"field": "fieldName", "value": "val1"}
```

### CRITICAL: Range Filter Format

```json
// Range filters use "field" (not "name"), and "valueFrom"/"valueTo"
{"field": "fieldName", "valueFrom": "2020-01-01", "valueTo": "2024-12-31"}
```

### All Fields Are Optional

An empty body `{}` is valid and returns default results.

### The `_odp_search_body()` Helper

```python
def _odp_search_body(
    q: str | None = None,
    filters: list[dict] | None = None,
    range_filters: list[dict] | None = None,
    offset: int = 0,
    limit: int = 25,
    sort_field: str | None = None,
    sort_order: str = "Desc",
) -> dict:
```

This builds the body dict, only including keys that have non-default values. `sort_order` values are `"Asc"` or `"Desc"` (capitalized).

---

## 8. Field Name System

### Auto-Expansion Map

The server auto-expands shorthand field names in `q` parameters:

| Short Name | Expands To |
|------------|------------|
| `patentNumber:` | `applicationMetaData.patentNumber:` |
| `inventionTitle:` | `applicationMetaData.inventionTitle:` |
| `firstApplicantName:` | `applicationMetaData.firstApplicantName:` |
| `filingDate:` | `applicationMetaData.filingDate:` |
| `grantDate:` | `applicationMetaData.grantDate:` |
| `appFilingDate:` | `applicationMetaData.filingDate:` |
| `firstNamedApplicant:` | `applicationMetaData.firstApplicantName:` |
| `examinerNameText:` | `applicationMetaData.examinerNameText:` |
| `applicationStatusDescriptionText:` | `applicationMetaData.applicationStatusDescriptionText:` |
| `applicationTypeLabelName:` | `applicationMetaData.applicationTypeLabelName:` |

**Note:** `applicationNumberText` is NOT in this map because it is already a top-level field (not nested under `applicationMetaData`).

### Key Searchable Fields (Full Reference)

**Application-Level:**
- `applicationNumberText` — Application number (digits only, e.g., "14876062")
- `applicationMetaData.patentNumber` — Granted patent number
- `applicationMetaData.inventionTitle` — Title
- `applicationMetaData.filingDate` — Filing date (YYYY-MM-DD)
- `applicationMetaData.grantDate` — Grant date
- `applicationMetaData.applicationStatusDescriptionText` — Status (e.g., "Patented Case")
- `applicationMetaData.applicationStatusCode` — Numeric status code
- `applicationMetaData.applicationTypeLabelName` — Type: Utility, Design, Plant, Re-Issue
- `applicationMetaData.applicationTypeCode` — UTL, DES, PLT, etc.
- `applicationMetaData.firstApplicantName` — First applicant
- `applicationMetaData.examinerNameText` — Examiner
- `applicationMetaData.groupArtUnitNumber` — Art unit
- `applicationMetaData.applicationConfirmationNumber` — Confirmation number

**Entity Status:**
- `applicationMetaData.entityStatusData.businessEntityStatusCategory` — Small, Micro, Regular Undiscounted

**Inventor Data:**
- `applicationMetaData.inventorBag.inventorNameText` — Full name
- `applicationMetaData.inventorBag.firstName` / `.lastName`

**Prosecution History:**
- `eventDataBag.eventCode`, `.eventDescriptionText`, `.eventDate`

**Continuity:**
- `parentContinuityBag`, `childContinuityBag`

**Full schema:** 274 fields in `resources/patent_data_schema.json`

---

## 9. HTTP Client & Retry Logic

### Shared Client Pool

```python
_client: httpx.AsyncClient | None = None

async def _get_client() -> httpx.AsyncClient:
    """Lazy singleton — one connection pool for all requests."""
```

Uses `httpx.AsyncClient` with a 60-second timeout, connection pooling, and redirect following.

### Three HTTP Helpers

| Helper | Content-Type | Used By |
|--------|-------------|---------|
| `_http_get(url, headers, params)` | N/A (query string) | ODP lookups, TSDR, DS-API fields |
| `_http_post_form(url, headers, data)` | `application/x-www-form-urlencoded` | DS-API search |
| `_http_post_json(url, headers, body)` | `application/json` | ODP search endpoints |

### Retry Strategy

```python
MAX_RETRIES = 3
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
```

- Exponential backoff: 1s, 2s, 4s
- Only retries on transient errors (429/5xx)
- Non-retryable errors (400, 403, 404) raise immediately
- Last exception is re-raised after all retries exhausted

### WAF Detection

```python
def _is_html(result: Any) -> bool:
```

Checks if a response contains HTML (`<!doctype` or `<html`). This indicates an AWS WAF block or redirect to the web UI.

### Response Truncation

```python
def _truncate_json(data: dict, max_chars: int = 50000) -> str:
```

Prevents overly large responses from exceeding MCP message limits. Truncates at 50K characters with a note.

---

## 10. Docker Deployment

### Dockerfile

```dockerfile
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py .
RUN useradd --create-home appuser
USER appuser
ENTRYPOINT ["python", "server.py"]
```

Key points:
- `PYTHONUNBUFFERED=1` — Required for stdio MCP transport (prevents buffering)
- Non-root user (`appuser`) for security
- Only `server.py` and `requirements.txt` are copied (no resources/ dir needed at runtime)
- No `CMD` — the entrypoint IS the server

### Build & Run

```bash
# Build
docker build -t uspto-mcp-server:latest .

# Run (for testing)
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"capabilities":{}}}' | \
  docker run -i --rm -e USPTO_API_KEY=your_key_here uspto-mcp-server:latest

# Verify tools are registered
echo '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' | \
  docker run -i --rm -e USPTO_API_KEY=your_key_here uspto-mcp-server:latest
```

### Dependencies (`requirements.txt`)

```
mcp[cli]>=1.0.0
httpx>=0.27.0
```

That's it. Two dependencies. `mcp[cli]` pulls in FastMCP, JSON-RPC handling, and stdio transport.

---

## 11. Docker MCP Gateway Integration

### Catalog Definition (`catalog.yaml`)

The server is registered in the Docker MCP Gateway catalog:

```yaml
registry:
  uspto:
    image: uspto-mcp-server:latest
    secrets:
      - name: uspto.api_key
        env: USPTO_API_KEY
      - name: patentsview.api_key
        env: PATENTSVIEW_API_KEY
    env:
      - name: USPTO_API_KEY
        value: '{{uspto.api_key}}'
      - name: PATENTSVIEW_API_KEY
        value: '{{patentsview.api_key}}'
```

### Secret → Env Var Flow

```
Docker MCP Gateway secret "uspto.api_key"
    → mapped to env var USPTO_API_KEY via catalog.yaml
        → read by server.py via os.environ.get("USPTO_API_KEY")
            → injected into x-api-key header by _odp_headers()
            → injected into USPTO-API-KEY header by _tsdr_headers()
```

**Common failure mode:** The secret is set but the `env` mapping in `catalog.yaml` is missing or wrong, causing the container to start with an empty `USPTO_API_KEY`.

---

## 12. Edge Cases & Gotchas

### 12.1 Application Number Formatting

Users provide application numbers in many formats. The server strips slashes, commas, and spaces:

```python
clean = application_number.replace("/", "").replace(",", "").replace(" ", "")
# "14/876,062" → "14876062"
# "14 876 062" → "14876062"
```

The ODP API expects **digits only** (e.g., `14876062`).

### 12.2 Patent Number Cleaning

Patent numbers come with prefixes and suffixes. The server strips them:

```python
clean = patent_number.upper().replace("US", "").replace(" ", "")
for suffix in ["B2", "B1", "A1", "A2", "A"]:
    if clean.endswith(suffix):
        clean = clean[:-len(suffix)]
# "US9524132B2" → "9524132"
```

### 12.3 TSDR Case Identifiers

TSDR expects case identifiers as `{type}{number}` concatenated:
- Serial number: `sn97123456`
- Registration number: `rn1234567`
- Reference number: `ref12345`
- International registration: `ir1234567`

### 12.4 DS-API Uses Form-Encoded POST

Unlike ODP (JSON POST) and TSDR (GET), the DS-API uses `application/x-www-form-urlencoded` POST:

```python
data = {
    "criteria": query,      # Lucene query syntax
    "start": str(start),
    "rows": str(min(rows, 100)),
}
```

### 12.5 `q` Parameter vs Filters

The `q` parameter already accepts the full query DSL including field:value pairs, ranges, and booleans. The `filters` and `rangeFilters` in the POST body provide **additional** structured filtering.

**Previous bug:** An earlier version of the server tried to parse `q` into structured filters. This was removed because it was lossy and unnecessary — just pass `q` through directly.

### 12.6 Sort Field Varies by Endpoint

Each search endpoint may have different sortable fields:
- Patent search: `applicationMetaData.filingDate`
- PTAB proceedings: `trialMetaData.petitionFilingDate`
- Petition decisions: `decisionDate`
- Appeals: `appealMetaData.appealLastModifiedDate`
- Interferences: `interferenceMetaData.interferenceLastModifiedDate`

**Text fields cannot be used for sorting** (API returns 400).

### 12.7 Logging to stderr Only

```python
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
```

MCP uses stdio. Any output to stdout that isn't valid JSON-RPC will break the protocol. All logging, debugging, and error output MUST go to stderr.

### 12.8 Empty `q` Handling

Different tools handle empty queries differently:
- `patent_search`: Passes `None` (omits `q` from body)
- `ptab_search`: Passes `""` (empty string)
- `patent_status_codes`: Passes `None`

An empty body `{}` is valid for all search endpoints and returns default results.

### 12.9 PatentsView Query Translation

The `_translate_to_patentsview_query()` function converts ODP DSL to PatentsView's JSON query format. This is a best-effort translation:
- Field names are mapped via `_ODP_TO_PV_FIELDS`
- Wildcards become `_text_any` queries
- Exact fields use direct equality
- Date ranges become `_gte`/`_lte` pairs
- `AND`/`OR` combinators are preserved

If translation fails, PatentsView supplementation is silently skipped.

---

## 13. Troubleshooting Playbook

### "API returned HTML instead of JSON"

**Cause:** AWS WAF is blocking the request. Typically means:
- Missing or invalid `x-api-key` header
- Request from a blocked IP or region
- Malformed request that triggers WAF rules

**Fix:** Verify `USPTO_API_KEY` env var is set and valid. Test with curl:
```bash
curl -s -H "x-api-key: YOUR_KEY" \
  "https://api.uspto.gov/api/v1/patent/applications/14876062" | head -c 200
```

### "403 Forbidden"

**Cause:** API key is invalid, expired, or not activated for `api.uspto.gov`.

**Fix:**
1. Check key at https://account.uspto.gov/api-manager/
2. Try the key in Swagger UI at https://data.uspto.gov/swagger/index.html (click Authorize)
3. Regenerate key if needed

### "400 Bad Request — Please use the api.uspto.gov endpoint"

**Cause:** You're hitting `data.uspto.gov` instead of `api.uspto.gov`.

**Fix:** Verify `ODP_BASE_URL = "https://api.uspto.gov"` in server.py.

### "400 Bad Request — Invalid request, review patent data request filter section"

**Cause:** Malformed POST body, usually wrong filter format.

**Fix:** Check filter format:
```json
// CORRECT
{"name": "fieldName", "value": ["val"]}

// WRONG
{"field": "fieldName", "value": "val"}
```

### Docker container starts but tools don't work

**Cause:** `USPTO_API_KEY` not passed to container.

**Fix:** Check env mapping in `catalog.yaml`. Run container manually with `-e USPTO_API_KEY=...` to verify.

### "Error: USPTO_API_KEY environment variable is not set"

**Cause:** Env var is empty or missing at container startup.

**Fix:** Set the env var:
```bash
docker run -e USPTO_API_KEY=your_key ...
```

For Docker MCP Gateway, verify secret mapping in `catalog.yaml`.

---

## 14. Rebuilding from Scratch

If you need to rebuild this server from zero, here is the complete recipe.

### Step 1: Project Structure

```
uspto-mcp-server/
├── server.py           # The entire server (single file)
├── requirements.txt    # mcp[cli]>=1.0.0, httpx>=0.27.0
├── Dockerfile          # Python 3.12-slim, stdio entrypoint
├── catalog.yaml        # Docker MCP Gateway registration
├── swagger.yaml        # Official ODP OpenAPI 3.0.1 spec (reference)
└── resources/          # Reference docs (not needed at runtime)
    ├── USPTO_ODP_API_Reference.md
    ├── patent_data_schema.json
    └── README.md
```

### Step 2: server.py Blueprint

```python
# 1. Imports: asyncio, os, re, sys, json, logging, httpx, FastMCP
# 2. Logging → stderr (CRITICAL for stdio MCP)
# 3. Config: env vars for API keys, base URLs for 4 backends
# 4. FastMCP("USPTO") initialization
# 5. Header builders: _tsdr_headers(), _ds_api_headers(), _odp_headers(), _patentsview_headers()
# 6. HTTP helpers with retry: _get_client(), _http_get(), _http_post_form(), _http_post_json()
# 7. PatentsView helpers: field maps, query translator, search function
# 8. Utilities: _is_html(), _truncate_json()
# 9. ODP helpers: _FIELD_NAME_MAP, _expand_field_names(), _odp_search_body()
# 10. 20 @mcp.tool() functions
# 11. if __name__ == "__main__": mcp.run(transport="stdio")
```

### Step 3: Key Implementation Rules

1. **All `@mcp.tool()` functions must be `async`** and return `str`
2. **Every tool must check `USPTO_API_KEY`** at the top (except DS-API tools which don't need it)
3. **Every tool must catch exceptions** and return user-friendly error strings (never raise)
4. **POST search tools** use `_odp_search_body()` + `_http_post_json()`
5. **GET lookup tools** use `_http_get()` with path parameters
6. **All responses pass through `_is_html()` check** before processing
7. **Large responses pass through `_truncate_json()`** (50K char limit)
8. **Application numbers are cleaned** of slashes/commas/spaces
9. **Patent numbers are cleaned** of US prefix and B1/B2/A1/A2 suffixes

### Step 4: The POST Search Body Builder

```python
def _odp_search_body(q=None, filters=None, range_filters=None,
                      offset=0, limit=25, sort_field=None, sort_order="Desc"):
    body = {}
    if q:
        body["q"] = q
    if filters:
        body["filters"] = filters  # [{"name": "...", "value": [...]}]
    if range_filters:
        body["rangeFilters"] = range_filters  # [{"field": "...", "valueFrom": "...", "valueTo": "..."}]
    body["pagination"] = {"offset": offset, "limit": min(limit, 100)}
    if sort_field:
        body["sort"] = [{"field": sort_field, "order": sort_order}]
    return body
```

### Step 5: Retry Logic

```python
MAX_RETRIES = 3
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}

# For each request:
for attempt in range(MAX_RETRIES):
    response = await client.get/post(...)
    if response.status_code in RETRY_STATUS_CODES and attempt < MAX_RETRIES - 1:
        await asyncio.sleep(2 ** attempt)  # 1s, 2s, 4s
        continue
    response.raise_for_status()
    return response.json()
```

### Step 6: Docker Build

```bash
docker build -t uspto-mcp-server:latest .
```

### Step 7: Verify

```bash
# Should print JSON-RPC response with 20 tools listed
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"capabilities":{}}}' | \
  docker run -i --rm -e USPTO_API_KEY=your_key uspto-mcp-server:latest
```

---

## 15. File Inventory

| File | Lines | Purpose | Runtime? |
|------|-------|---------|----------|
| `server.py` | ~1252 | Complete MCP server implementation | Yes |
| `requirements.txt` | 2 | Python dependencies | Build only |
| `Dockerfile` | 12 | Container definition | Build only |
| `catalog.yaml` | 64 | Docker MCP Gateway catalog registration | Gateway config |
| `swagger.yaml` | 2624 | Official ODP OpenAPI 3.0.1 spec | Reference only |
| `resources/USPTO_ODP_API_Reference.md` | 372 | Compiled API reference from official docs | Reference only |
| `resources/patent_data_schema.json` | ~5000+ | Full 274-field JSON schema | Reference only |
| `resources/README.md` | 33 | Resource directory index | Reference only |
| `.firecrawl/swagger.md` | varies | Scraped Swagger UI content | Reference only |

---

## 16. Known Issues & Future Work

### Known Issues

1. **API Key activation uncertainty** — The key may need manual activation at https://account.uspto.gov/api-manager/ for `api.uspto.gov`. If you get 403, this is the first thing to check.

2. **PatentsView key grants suspended** — New API key registration at patentsview.org is temporarily suspended. The `PATENTSVIEW_API_KEY` functionality works but you cannot get a new key.

3. **catalog.yaml tool list is stale** — Lists 12 tools (from before the rewrite) instead of the current 20. Should be updated.

4. **GET search not exposed** — The `GET /api/v1/patent/applications/search` endpoint accepts query-string parameters. We only use POST (more powerful), but GET could be useful for simple queries or debugging.

5. **Download endpoint not exposed** — `GET /api/v1/patent/applications/search/download` (max 6MB CSV/JSON) not exposed as a tool.

### Future Work

- **Add document download tool** — Two-step flow: get document metadata, then download PDF via `downloadUrl` from `downloadOptionBag`
- **Add faceted search** — ODP supports `facets` in POST body for aggregation
- **Add `fields` parameter** — Allow users to specify which fields to return (reduces response size)
- **Add PatentsView pre-grant publication search** — `pg_patent` endpoint for published applications
- **Rate limiting** — Implement client-side rate limiting (currently relies on retry-on-429)
- **Health check endpoint** — Add a simple tool that pings the API to verify key/connectivity

---

## 17. Reference Links

| Resource | URL |
|----------|-----|
| ODP Getting Started | https://data.uspto.gov/apis/getting-started |
| Swagger UI | https://data.uspto.gov/swagger/index.html |
| Swagger YAML | https://data.uspto.gov/swagger/swagger.yaml |
| API Key Management | https://account.uspto.gov/api-manager/ |
| Patent Data Schema (274 fields) | https://data.uspto.gov/documents/documents/patent-data-schema.json |
| PEDS→ODP Migration Guide | https://data.uspto.gov/documents/documents/PEDS-to-ODP-API-Mapping.pdf |
| ODP Query Syntax Spec | https://data.uspto.gov/documents/documents/ODP-API-Query-Spec.pdf |
| API Rate Limits | https://data.uspto.gov/apis/api-rate-limits |
| PatentsView API | https://search.patentsview.org |
| TSDR API | https://tsdrapi.uspto.gov |
| DS-API | https://developer.uspto.gov/ds-api |
| MCP Specification | https://modelcontextprotocol.io |
| FastMCP Docs | https://github.com/modelcontextprotocol/python-sdk |
| httpx Docs | https://www.python-httpx.org |

---

## Appendix A: Complete curl Examples

### Patent Search (POST)
```bash
curl -X POST "https://api.uspto.gov/api/v1/patent/applications/search" \
  -H "x-api-key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"q":"applicationMetaData.inventionTitle:\"artificial intelligence\"","pagination":{"offset":0,"limit":5}}'
```

### Patent Lookup (GET)
```bash
curl -X GET "https://api.uspto.gov/api/v1/patent/applications/14876062" \
  -H "x-api-key: YOUR_KEY" \
  -H "Accept: application/json"
```

### PTAB Proceedings Search (POST)
```bash
curl -X POST "https://api.uspto.gov/api/v1/patent/trials/proceedings/search" \
  -H "x-api-key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"q":"IPR2023","pagination":{"offset":0,"limit":10}}'
```

### Petition Decisions Search (POST)
```bash
curl -X POST "https://api.uspto.gov/api/v1/petition/decisions/search" \
  -H "x-api-key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Trademark Status (GET)
```bash
curl -X GET "https://tsdrapi.uspto.gov/ts/cd/casestatus/sn97123456/info" \
  -H "USPTO-API-KEY: YOUR_KEY" \
  -H "Accept: application/json"
```

### DS-API Dataset Search (POST form-encoded)
```bash
curl -X POST "https://developer.uspto.gov/ds-api/oa_citations/v1/records" \
  -H "Accept: application/json" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "criteria=patent_title:artificial&start=0&rows=10"
```

### Bulk Data Products (GET)
```bash
curl -X GET "https://api.uspto.gov/api/v1/datasets/products/search?latest=true" \
  -H "x-api-key: YOUR_KEY" \
  -H "Accept: application/json"
```
