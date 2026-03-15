"""USPTO MCP Server - Model Context Protocol server for the USPTO APIs.

Patent tools use api.uspto.gov (ODP v2) as primary backend with structured
JSON POST requests. PatentsView (search.patentsview.org) is available as a
supplementary source for granted patent data. Trademark tools use TSDR API.
"""

import asyncio
import os
import re
import sys
import json
import logging
import httpx
from typing import Any
from mcp.server.fastmcp import FastMCP

# Configure logging to stderr so it doesn't interfere with stdio MCP transport
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("uspto-mcp-server")

# --- Configuration ---
USPTO_API_KEY = os.environ.get("USPTO_API_KEY", "")
PATENTSVIEW_API_KEY = os.environ.get("PATENTSVIEW_API_KEY", "")
TSDR_BASE_URL = "https://tsdrapi.uspto.gov"
DS_API_BASE_URL = "https://developer.uspto.gov/ds-api"
ODP_BASE_URL = "https://api.uspto.gov"
PATENTSVIEW_BASE_URL = "https://search.patentsview.org"

# Rate limit: 60 req/min for TSDR, 4 req/min for PDF/ZIP downloads

# --- Initialize MCP Server ---
mcp = FastMCP("USPTO")


# --- Header builders ---

def _tsdr_headers() -> dict:
    headers = {"Accept": "application/json"}
    if USPTO_API_KEY:
        headers["USPTO-API-KEY"] = USPTO_API_KEY
    return headers


def _ds_api_headers() -> dict:
    return {"Accept": "application/json"}


def _odp_headers() -> dict:
    """Headers for api.uspto.gov — uses lowercase x-api-key and JSON content type."""
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if USPTO_API_KEY:
        headers["x-api-key"] = USPTO_API_KEY
    return headers


def _patentsview_headers() -> dict:
    headers = {"Accept": "application/json"}
    if PATENTSVIEW_API_KEY:
        headers["X-Api-Key"] = PATENTSVIEW_API_KEY
    return headers


# --- ODP Search Request Builder ---

def _odp_search_body(
    q: str | None = None,
    filters: list[dict] | None = None,
    range_filters: list[dict] | None = None,
    offset: int = 0,
    limit: int = 25,
    sort_field: str | None = None,
    sort_order: str = "Desc",
) -> dict:
    """Build the standard JSON body for api.uspto.gov POST search endpoints.

    The ODP v2 API uses a consistent request format:
      { q, filters, rangeFilters, pagination: {offset, limit}, sort: [{field, order}] }

    Filters use the format: {"name": "<fieldName>", "value": ["val1", ...]}
    """
    body: dict[str, Any] = {
        "q": q if q else None,
        "filters": filters or [],
        "rangeFilters": range_filters or [],
        "pagination": {
            "offset": offset,
            "limit": min(limit, 100),
        },
    }
    if sort_field:
        body["sort"] = [{"field": sort_field, "order": sort_order}]
    else:
        body["sort"] = []
    return body


# --- Shared HTTP client with retry ---
_RETRY_STATUSES = {429, 500, 502, 503, 504}
_MAX_RETRIES = 2
_RETRY_BACKOFF = 1.0  # seconds, doubles each retry

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
    return _client


def _parse_response(resp: httpx.Response) -> dict | str:
    content_type = resp.headers.get("content-type", "")
    if "json" in content_type:
        return resp.json()
    elif "xml" in content_type:
        return resp.text
    else:
        try:
            return resp.json()
        except Exception:
            return resp.text


async def _http_get(url: str, headers: dict, params: dict | None = None) -> dict | str:
    client = _get_client()
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            resp = await client.get(url, headers=headers, params=params)
            if resp.status_code in _RETRY_STATUSES and attempt < _MAX_RETRIES:
                wait = _RETRY_BACKOFF * (2 ** attempt)
                logger.info("HTTP %s from %s, retrying in %.1fs", resp.status_code, url, wait)
                await asyncio.sleep(wait)
                continue
            resp.raise_for_status()
            return _parse_response(resp)
        except (httpx.ConnectTimeout, httpx.ReadTimeout) as e:
            last_exc = e
            if attempt < _MAX_RETRIES:
                wait = _RETRY_BACKOFF * (2 ** attempt)
                logger.info("Timeout on %s, retrying in %.1fs", url, wait)
                await asyncio.sleep(wait)
                continue
            raise
    raise last_exc  # type: ignore[misc]


async def _http_post_form(url: str, headers: dict, data: dict) -> dict | str:
    """POST with form-encoded body (used by DS-API)."""
    client = _get_client()
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            resp = await client.post(url, headers=headers, data=data)
            if resp.status_code in _RETRY_STATUSES and attempt < _MAX_RETRIES:
                wait = _RETRY_BACKOFF * (2 ** attempt)
                logger.info("HTTP %s from %s, retrying in %.1fs", resp.status_code, url, wait)
                await asyncio.sleep(wait)
                continue
            resp.raise_for_status()
            return _parse_response(resp)
        except (httpx.ConnectTimeout, httpx.ReadTimeout) as e:
            last_exc = e
            if attempt < _MAX_RETRIES:
                wait = _RETRY_BACKOFF * (2 ** attempt)
                logger.info("Timeout on %s, retrying in %.1fs", url, wait)
                await asyncio.sleep(wait)
                continue
            raise
    raise last_exc  # type: ignore[misc]


async def _http_post_json(url: str, headers: dict, json_body: dict) -> dict | str:
    """POST with JSON body (used by api.uspto.gov ODP v2 endpoints)."""
    client = _get_client()
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            resp = await client.post(url, headers=headers, json=json_body)
            if resp.status_code in _RETRY_STATUSES and attempt < _MAX_RETRIES:
                wait = _RETRY_BACKOFF * (2 ** attempt)
                logger.info("HTTP %s from %s, retrying in %.1fs", resp.status_code, url, wait)
                await asyncio.sleep(wait)
                continue
            resp.raise_for_status()
            return _parse_response(resp)
        except (httpx.ConnectTimeout, httpx.ReadTimeout) as e:
            last_exc = e
            if attempt < _MAX_RETRIES:
                wait = _RETRY_BACKOFF * (2 ** attempt)
                logger.info("Timeout on %s, retrying in %.1fs", url, wait)
                await asyncio.sleep(wait)
                continue
            raise
    raise last_exc  # type: ignore[misc]


# --- PatentsView helpers (supplementary source) ---

_PV_DEFAULT_FIELDS = [
    "patent_id", "patent_title", "patent_date", "patent_abstract",
    "patent_type", "patent_num_claims",
    "inventors.inventor_first_name", "inventors.inventor_last_name",
    "assignees.assignee_organization",
    "application.application_number", "application.filing_date",
]

_PV_PREGRANT_FIELDS = [
    "document_number", "invention_title", "publication_date",
    "abstract", "publication_type",
    "inventors.inventor_first_name", "inventors.inventor_last_name",
    "assignees.assignee_organization",
    "application.application_number", "application.filing_date",
]

_ODP_TO_PV_FIELDS = {
    "patentNumber": "patent_id",
    "inventionTitle": "patent_title",
    "firstNamedApplicant": "assignees.assignee_organization",
    "applicationNumberText": "application.application_number",
    "appFilingDate": "application.filing_date",
}

_PV_EXACT_FIELDS = {"patent_id", "application.application_number"}


def _translate_to_patentsview_query(odp_query: str) -> str:
    """Translate user query to PatentsView JSON query string."""
    odp_query = odp_query.strip()
    if not odp_query:
        return json.dumps({"_text_any": {"patent_title": ""}})

    parts = re.split(r'\s+(AND|OR)\s+', odp_query)
    clauses = []
    operators = []

    for part in parts:
        part = part.strip()
        if part in ("AND", "OR"):
            operators.append(part)
            continue

        m = re.match(r'^(\w+):\s*(.+)$', part)
        if m:
            field_name, value = m.group(1), m.group(2).strip()
            pv_field = _ODP_TO_PV_FIELDS.get(field_name, "patent_title")

            date_m = re.match(r'^\[(\S+)\s+TO\s+(\S+)\]$', value)
            if date_m:
                clauses.append({"_and": [
                    {"_gte": {pv_field: date_m.group(1)}},
                    {"_lte": {pv_field: date_m.group(2)}},
                ]})
            elif value.startswith('"') and value.endswith('"'):
                inner = value.strip('"')
                if pv_field in _PV_EXACT_FIELDS:
                    clauses.append({pv_field: inner})
                else:
                    clauses.append({"_contains": {pv_field: inner}})
            elif '*' in value:
                clauses.append({"_text_any": {pv_field: value.replace('*', '')}})
            elif pv_field in _PV_EXACT_FIELDS:
                clauses.append({pv_field: value})
            else:
                clauses.append({"_contains": {pv_field: value}})
        else:
            clauses.append({"_text_any": {"patent_title": part}})

    if len(clauses) == 0:
        return json.dumps({"_text_any": {"patent_title": odp_query}})
    if len(clauses) == 1:
        return json.dumps(clauses[0])

    has_or = "OR" in operators
    combinator = "_or" if has_or and "AND" not in operators else "_and"
    return json.dumps({combinator: clauses})


async def _patentsview_search(
    q: str,
    fields: list[str] | None = None,
    size: int = 25,
    endpoint: str = "patent",
) -> dict:
    """Query PatentsView API. endpoint is 'patent' for grants or 'pg_patent' for pre-grant pubs."""
    url = f"{PATENTSVIEW_BASE_URL}/api/v1/{endpoint}/"
    headers = _patentsview_headers()
    params: dict[str, str] = {"q": q}

    if fields:
        params["f"] = json.dumps(fields)
    elif endpoint == "pg_patent":
        params["f"] = json.dumps(_PV_PREGRANT_FIELDS)
    else:
        params["f"] = json.dumps(_PV_DEFAULT_FIELDS)
    params["o"] = json.dumps({"size": min(size, 100)})

    result = await _http_get(url, headers, params)
    if isinstance(result, dict):
        return result
    return json.loads(result) if isinstance(result, str) else {}


# --- Utility functions ---

def _is_html(result: Any) -> bool:
    """Check if result is HTML instead of expected JSON (WAF block indicator)."""
    if isinstance(result, str) and ("<!doctype" in result.lower() or "<html" in result.lower()):
        return True
    return False


def _truncate_json(data: dict, max_chars: int = 50000) -> str:
    """Serialize JSON, truncating if too large."""
    s = json.dumps(data, indent=2)
    if len(s) > max_chars:
        return s[:max_chars] + f"\n... [truncated, {len(s)} total chars]"
    return s


# --- ODP field name expansion ---

_FIELD_NAME_MAP = {
    "patentNumber:": "applicationMetaData.patentNumber:",
    "inventionTitle:": "applicationMetaData.inventionTitle:",
    "firstApplicantName:": "applicationMetaData.firstApplicantName:",
    "filingDate:": "applicationMetaData.filingDate:",
    "grantDate:": "applicationMetaData.grantDate:",
    "appFilingDate:": "applicationMetaData.filingDate:",
    "firstNamedApplicant:": "applicationMetaData.firstApplicantName:",
    "examinerNameText:": "applicationMetaData.examinerNameText:",
    "applicationStatusDescriptionText:": "applicationMetaData.applicationStatusDescriptionText:",
    "applicationTypeLabelName:": "applicationMetaData.applicationTypeLabelName:",
}


def _expand_field_names(q: str) -> str:
    """Expand short field names to fully-qualified ODP field names in a query string.

    For example: "patentNumber:9524132" becomes "applicationMetaData.patentNumber:9524132"
    The field applicationNumberText is already top-level and stays as-is.
    """
    if not q:
        return q
    result = q
    for short, full in _FIELD_NAME_MAP.items():
        result = result.replace(short, full)
    return result


# ============================================================
# TOOL 1: Trademark Case Status
# ============================================================
@mcp.tool()
async def trademark_status(
    case_id: str,
    id_type: str = "sn",
) -> str:
    """Look up the status of a US trademark application or registration. case_id is the identifier number. id_type is one of sn (serial number, default), rn (registration number), ref (reference number), ir (international registration)."""
    if not USPTO_API_KEY:
        return "Error: USPTO_API_KEY environment variable is not set. Please configure your API key."

    valid_types = ("sn", "rn", "ref", "ir")
    if id_type not in valid_types:
        return f"Error: id_type must be one of {valid_types}, got '{id_type}'"

    case_identifier = f"{id_type}{case_id}"
    url = f"{TSDR_BASE_URL}/ts/cd/casestatus/{case_identifier}/info"
    headers = _tsdr_headers()

    try:
        result = await _http_get(url, headers)
        if isinstance(result, dict):
            return json.dumps(result, indent=2)
        return str(result)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"No trademark found for {id_type.upper()} {case_id}"
        elif e.response.status_code == 400:
            return f"Invalid case ID format: {case_id} (type: {id_type})"
        elif e.response.status_code == 204:
            return f"Case {id_type.upper()} {case_id} exists but is not registered or has no data."
        return f"TSDR API error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error looking up trademark: {str(e)}"


# ============================================================
# TOOL 2: Multi-Case Trademark Status
# ============================================================
@mcp.tool()
async def trademark_multi_status(
    case_ids: str,
    id_type: str = "sn",
) -> str:
    """Look up the status of multiple trademark cases at once. case_ids is a comma-separated string of identifier numbers. id_type is one of sn (default), rn, ref, ir."""
    if not USPTO_API_KEY:
        return "Error: USPTO_API_KEY environment variable is not set."

    valid_types = ("sn", "rn", "ref", "ir")
    if id_type not in valid_types:
        return f"Error: id_type must be one of {valid_types}"

    url = f"{TSDR_BASE_URL}/ts/cd/caseMultiStatus/{id_type}"
    headers = _tsdr_headers()
    params = {"ids": case_ids}

    try:
        result = await _http_get(url, headers, params)
        if isinstance(result, dict):
            return json.dumps(result, indent=2)
        return str(result)
    except httpx.HTTPStatusError as e:
        return f"TSDR API error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error: {str(e)}"


# ============================================================
# TOOL 3: Trademark Document Info
# ============================================================
@mcp.tool()
async def trademark_documents(
    case_id: str,
    id_type: str = "sn",
) -> str:
    """List all prosecution documents for a trademark case. case_id is the identifier number. id_type is one of sn (default), rn, ref, ir."""
    if not USPTO_API_KEY:
        return "Error: USPTO_API_KEY environment variable is not set."

    case_identifier = f"{id_type}{case_id}"
    url = f"{TSDR_BASE_URL}/ts/cd/casedocs/{case_identifier}/info"
    headers = _tsdr_headers()

    try:
        result = await _http_get(url, headers)
        if isinstance(result, dict):
            return json.dumps(result, indent=2)
        return str(result)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"No documents found for {id_type.upper()} {case_id}"
        return f"TSDR API error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error: {str(e)}"


# ============================================================
# TOOL 4: Trademark Last Update
# ============================================================
@mcp.tool()
async def trademark_last_update(
    serial_number: str,
) -> str:
    """Check when a trademark case was last updated in the prosecution history. serial_number is the US serial number of the trademark application."""
    if not USPTO_API_KEY:
        return "Error: USPTO_API_KEY environment variable is not set."

    url = f"{TSDR_BASE_URL}/last-update/info.json"
    headers = _tsdr_headers()
    params = {"sn": serial_number}

    try:
        result = await _http_get(url, headers, params)
        if isinstance(result, dict):
            return json.dumps(result, indent=2)
        return str(result)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"No case found for serial number {serial_number}"
        return f"TSDR API error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error: {str(e)}"


# ============================================================
# TOOL 5: List USPTO Datasets (DS-API)
# ============================================================
@mcp.tool()
async def list_datasets() -> str:
    """List all available USPTO datasets that can be searched via the DS-API. Returns dataset names, versions, and documentation URLs."""
    url = f"{DS_API_BASE_URL}/"
    headers = _ds_api_headers()

    try:
        result = await _http_get(url, headers)
        if isinstance(result, dict):
            return json.dumps(result, indent=2)
        return str(result)
    except Exception as e:
        return f"Error listing datasets: {str(e)}"


# ============================================================
# TOOL 6: List Dataset Fields (DS-API)
# ============================================================
@mcp.tool()
async def list_dataset_fields(
    dataset: str = "oa_citations",
    version: str = "v1",
) -> str:
    """List the searchable fields for a specific USPTO dataset. dataset defaults to oa_citations. version defaults to v1. Use list_datasets to see available datasets."""
    url = f"{DS_API_BASE_URL}/{dataset}/{version}/fields"
    headers = _ds_api_headers()

    try:
        result = await _http_get(url, headers)
        if isinstance(result, dict):
            return json.dumps(result, indent=2)
        return str(result)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"Dataset '{dataset}' version '{version}' not found. Use list_datasets() to see available datasets."
        return f"DS-API error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error: {str(e)}"


# ============================================================
# TOOL 7: Search USPTO Dataset (DS-API)
# ============================================================
@mcp.tool()
async def search_dataset(
    query: str,
    dataset: str = "oa_citations",
    version: str = "v1",
    start: int = 0,
    rows: int = 25,
) -> str:
    """Search a USPTO dataset using Lucene query syntax. query uses Lucene syntax like patent_title:artificial. dataset defaults to oa_citations. start and rows control pagination (max 100 rows)."""
    url = f"{DS_API_BASE_URL}/{dataset}/{version}/records"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "criteria": query,
        "start": str(start),
        "rows": str(min(rows, 100)),
    }

    try:
        result = await _http_post_form(url, headers, data)
        if isinstance(result, (dict, list)):
            return json.dumps(result, indent=2)
        return str(result)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"No results found for query: {query}"
        return f"DS-API error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error: {str(e)}"


# ============================================================
# TOOL 8: Patent Search (ODP v2 primary, PatentsView supplementary)
# ============================================================
@mcp.tool()
async def patent_search(
    q: str,
    offset: int = 0,
    limit: int = 25,
) -> str:
    """Search for US patents and published applications via USPTO Open Data Portal.

    The q parameter accepts ODP DSL syntax directly. Short field names are
    automatically expanded to fully-qualified names.

    Query examples:
      - Plain keywords: "artificial intelligence"
      - By title: applicationMetaData.inventionTitle:"ink jet printer"
      - By applicant: applicationMetaData.firstApplicantName:Google
      - By patent number: applicationMetaData.patentNumber:9524132
      - By application number: applicationNumberText:14876062
      - Date range: applicationMetaData.filingDate:[2024-01-01 TO 2024-12-31]
      - Combined: applicationMetaData.inventionTitle:printer AND applicationMetaData.filingDate:[2024-01-01 TO 2024-12-31]

    Short aliases also work (auto-expanded):
      patentNumber, inventionTitle, firstApplicantName, filingDate, grantDate,
      appFilingDate, firstNamedApplicant, examinerNameText,
      applicationStatusDescriptionText, applicationTypeLabelName

    offset and limit control pagination (max 100 results per page).
    Requires USPTO_API_KEY (from developer.uspto.gov).
    """
    if not USPTO_API_KEY:
        return (
            "Error: USPTO_API_KEY is required for patent search. "
            "Register at developer.uspto.gov to get an API key."
        )

    # Expand short field names to fully-qualified ODP names
    expanded_q = _expand_field_names(q.strip()) if q and q.strip() else None

    body = _odp_search_body(
        q=expanded_q,
        offset=offset,
        limit=limit,
        sort_field="applicationMetaData.filingDate",
        sort_order="Desc",
    )

    url = f"{ODP_BASE_URL}/api/v1/patent/applications/search"
    headers = _odp_headers()

    try:
        result = await _http_post_json(url, headers, body)
        if _is_html(result):
            return "Error: API returned HTML instead of JSON. The API may be temporarily unavailable."
        if isinstance(result, dict):
            # Supplement with PatentsView if available
            if PATENTSVIEW_API_KEY:
                try:
                    pv_query = _translate_to_patentsview_query(q)
                    pv_result = await _patentsview_search(pv_query, size=limit, endpoint="patent")
                    grants = pv_result.get("patents", []) if isinstance(pv_result, dict) else []
                    if grants:
                        result["patentsview_grants"] = grants[:5]
                        result["patentsview_note"] = "Top 5 granted patent matches from PatentsView"
                except Exception as e:
                    logger.info("PatentsView supplemental search failed: %s", e)

            return _truncate_json(result)
        return str(result)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            return (
                "Error: USPTO API returned 403 Forbidden. "
                "Your API key may need activation for api.uspto.gov. "
                "Check https://account.uspto.gov/api-manager/ for key status."
            )
        if e.response.status_code == 400:
            return (
                f"Error: USPTO API returned 400 Bad Request. "
                f"The query may have invalid syntax. Try plain keywords instead.\n"
                f"Request body: {json.dumps(body, indent=2)}"
            )
        return f"USPTO API error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error searching patents: {str(e)}"


# ============================================================
# TOOL 9: Patent Lookup (ODP v2 primary, PatentsView supplementary)
# ============================================================
@mcp.tool()
async def patent_lookup(
    application_number: str = "",
    patent_number: str = "",
) -> str:
    """Look up a specific US patent or published application by number.

    Provide ONE of:
      - application_number: e.g. "14876062" or "14/876,062" (slashes/commas stripped)
      - patent_number: e.g. "9524132" or "US9524132B2" (prefix/suffix stripped)

    Returns filing dates, inventors, assignees, and application metadata.
    Requires USPTO_API_KEY (from developer.uspto.gov).
    """
    if not application_number and not patent_number:
        return "Error: provide either application_number or patent_number"

    if not USPTO_API_KEY:
        return "Error: USPTO_API_KEY is required. Register at developer.uspto.gov."

    headers = _odp_headers()

    if application_number:
        # Use direct GET endpoint for application number lookups
        clean = application_number.replace("/", "").replace(",", "").replace(" ", "")
        url = f"{ODP_BASE_URL}/api/v1/patent/applications/{clean}"
        pv_q = json.dumps({"application.application_number": clean})

        try:
            result = await _http_get(url, headers)
            if _is_html(result):
                return "Error: API returned HTML instead of JSON. The API may be temporarily unavailable."
            if isinstance(result, dict):
                # Supplement with PatentsView grant data
                if PATENTSVIEW_API_KEY:
                    try:
                        pv_result = await _patentsview_search(pv_q, size=5, endpoint="patent")
                        grants = pv_result.get("patents", []) if isinstance(pv_result, dict) else []
                        if grants:
                            result["patentsview_grants"] = grants
                    except Exception as e:
                        logger.info("PatentsView supplemental lookup failed: %s", e)
                return _truncate_json(result)
            return str(result)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                return "Error: USPTO API returned 403 Forbidden. Check your API key at https://account.uspto.gov/api-manager/"
            if e.response.status_code == 404:
                return f"No patent found for application {application_number}"
            return f"USPTO API error {e.response.status_code}: {e.response.text}"
        except Exception as e:
            return f"Error: {str(e)}"
    else:
        # Use POST search with q parameter for patent number lookups
        clean = patent_number.upper().replace("US", "").replace(" ", "")
        for suffix in ["B2", "B1", "A1", "A2", "A"]:
            if clean.endswith(suffix):
                clean = clean[:-len(suffix)]
        pv_q = json.dumps({"patent_id": clean})

        body = _odp_search_body(
            q=f"applicationMetaData.patentNumber:{clean}",
            limit=5,
        )
        url = f"{ODP_BASE_URL}/api/v1/patent/applications/search"

        try:
            result = await _http_post_json(url, headers, body)
            if _is_html(result):
                return "Error: API returned HTML instead of JSON. The API may be temporarily unavailable."
            if isinstance(result, dict):
                # Supplement with PatentsView grant data
                if PATENTSVIEW_API_KEY:
                    try:
                        pv_result = await _patentsview_search(pv_q, size=5, endpoint="patent")
                        grants = pv_result.get("patents", []) if isinstance(pv_result, dict) else []
                        if grants:
                            result["patentsview_grants"] = grants
                    except Exception as e:
                        logger.info("PatentsView supplemental lookup failed: %s", e)
                return _truncate_json(result)
            return str(result)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                return "Error: USPTO API returned 403 Forbidden. Check your API key at https://account.uspto.gov/api-manager/"
            if e.response.status_code == 404:
                return f"No patent found for patent {patent_number}"
            return f"USPTO API error {e.response.status_code}: {e.response.text}"
        except Exception as e:
            return f"Error: {str(e)}"


# ============================================================
# TOOL 10: Patent Documents (ODP v2)
# ============================================================
@mcp.tool()
async def patent_documents(
    application_number: str,
) -> str:
    """List all prosecution history documents for a patent application.

    application_number: e.g. "14876062" or "14/876,062" (slashes/commas stripped).

    Returns document metadata including mail dates, document codes, and descriptions.
    Use this to find office actions, responses, and other prosecution documents.
    Requires USPTO_API_KEY (register at developer.uspto.gov).
    """
    if not USPTO_API_KEY:
        return "Error: USPTO_API_KEY is required for patent documents. Register at developer.uspto.gov."

    clean = application_number.replace("/", "").replace(",", "").replace(" ", "")

    url = f"{ODP_BASE_URL}/api/v1/patent/applications/{clean}/documents"
    headers = _odp_headers()

    try:
        result = await _http_get(url, headers)
        if _is_html(result):
            return (
                "Error: API returned HTML instead of JSON. "
                "View documents directly at "
                f"https://data.uspto.gov/patent/applications/{clean}/documents"
            )
        if isinstance(result, dict):
            return _truncate_json(result)
        return str(result)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            return "Error: USPTO API returned 403 Forbidden. Check your USPTO_API_KEY."
        if e.response.status_code == 404:
            return f"No documents found for application {application_number}"
        return f"USPTO API error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error: {str(e)}"


# ============================================================
# TOOL 11: ODP Bulk Data Products
# ============================================================
@mcp.tool()
async def list_bulk_data_products(
    search_query: str = "",
) -> str:
    """List available USPTO bulk data products for download. search_query optionally filters by keyword like Grants or Trademarks. Requires USPTO_API_KEY."""
    if not USPTO_API_KEY:
        return "Error: USPTO_API_KEY is required. Register at developer.uspto.gov."

    url = f"{ODP_BASE_URL}/api/v1/datasets/products/search"
    headers = _odp_headers()

    params: dict[str, Any] = {"latest": "true"}
    if search_query:
        params["productTitle"] = search_query

    try:
        result = await _http_get(url, headers, params)
        if _is_html(result):
            return "Error: API returned HTML. Browse products at https://data.uspto.gov/apis/datasets"
        if isinstance(result, dict):
            return json.dumps(result, indent=2)
        return str(result)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            return "Error: USPTO API returned 403 Forbidden. Check your USPTO_API_KEY."
        return f"USPTO API error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error: {str(e)}"


# ============================================================
# TOOL 12: PTAB Proceedings Search (ODP v2 — POST)
# ============================================================
@mcp.tool()
async def ptab_search(
    query: str = "",
    offset: int = 0,
    limit: int = 25,
) -> str:
    """Search Patent Trial and Appeal Board (PTAB) proceedings.

    query can be a keyword, patent number, party name, or proceeding number
    like IPR2023-00123. Leave empty to browse recent proceedings.
    offset and limit control pagination (max 100).
    Requires USPTO_API_KEY.
    """
    if not USPTO_API_KEY:
        return "Error: USPTO_API_KEY is required for PTAB search. Register at developer.uspto.gov."

    body = _odp_search_body(
        q=query if query else "",
        offset=offset,
        limit=limit,
        sort_field="trialMetaData.petitionFilingDate",
        sort_order="Desc",
    )

    url = f"{ODP_BASE_URL}/api/v1/patent/trials/proceedings/search"
    headers = _odp_headers()

    try:
        result = await _http_post_json(url, headers, body)
        if _is_html(result):
            return "Error: API returned HTML. Search PTAB at https://data.uspto.gov/ptab"
        if isinstance(result, dict):
            return _truncate_json(result)
        return str(result)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            return "Error: USPTO API returned 403 Forbidden. Check your USPTO_API_KEY."
        return f"PTAB search error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error searching PTAB: {str(e)}"


# ============================================================
# TOOL 13: Petition Decisions Search (ODP v2 — NEW)
# ============================================================
@mcp.tool()
async def petition_decisions_search(
    query: str = "",
    offset: int = 0,
    limit: int = 25,
) -> str:
    """Search USPTO petition decisions.

    query can be a keyword or application number. Leave empty to browse recent decisions.
    offset and limit control pagination (max 100).
    Requires USPTO_API_KEY.
    """
    if not USPTO_API_KEY:
        return "Error: USPTO_API_KEY is required. Register at developer.uspto.gov."

    body = _odp_search_body(
        q=query if query else "",
        offset=offset,
        limit=limit,
        sort_field="decisionDate",
        sort_order="Desc",
    )

    url = f"{ODP_BASE_URL}/api/v1/petition/decisions/search"
    headers = _odp_headers()

    try:
        result = await _http_post_json(url, headers, body)
        if _is_html(result):
            return "Error: API returned HTML. The petition decisions API may be temporarily unavailable."
        if isinstance(result, dict):
            return _truncate_json(result)
        return str(result)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            return "Error: USPTO API returned 403 Forbidden. Check your USPTO_API_KEY."
        return f"Petition decisions error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error searching petition decisions: {str(e)}"


# ============================================================
# TOOL 14: Patent Appeals Decisions Search (ODP v2 — NEW)
# ============================================================
@mcp.tool()
async def patent_appeals_search(
    query: str = "",
    offset: int = 0,
    limit: int = 25,
) -> str:
    """Search patent appeal decisions from the Patent Trial and Appeal Board.

    query can be a keyword, application number, appeal number, or inventor name.
    Leave empty to browse recent decisions.
    Returns appeal outcomes, decision types, statutes cited, and document metadata.
    offset and limit control pagination (max 100).
    Requires USPTO_API_KEY.
    """
    if not USPTO_API_KEY:
        return "Error: USPTO_API_KEY is required. Register at developer.uspto.gov."

    body = _odp_search_body(
        q=query if query else "",
        offset=offset,
        limit=limit,
        sort_field="appealMetaData.appealLastModifiedDate",
        sort_order="Desc",
    )

    url = f"{ODP_BASE_URL}/api/v1/patent/appeals/decisions/search"
    headers = _odp_headers()

    try:
        result = await _http_post_json(url, headers, body)
        if _is_html(result):
            return "Error: API returned HTML. The appeals decisions API may be temporarily unavailable."
        if isinstance(result, dict):
            return _truncate_json(result)
        return str(result)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            return "Error: USPTO API returned 403 Forbidden. Check your USPTO_API_KEY."
        return f"Appeals decisions error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error searching appeals decisions: {str(e)}"


# ============================================================
# TOOL 15: Patent Interference Decisions Search (ODP v2 — NEW)
# ============================================================
@mcp.tool()
async def patent_interferences_search(
    query: str = "",
    offset: int = 0,
    limit: int = 25,
) -> str:
    """Search patent interference decisions.

    query can be a keyword, interference number, patent number, or party name.
    Leave empty to browse recent decisions.
    Returns senior/junior party data, decision documents, and outcomes.
    offset and limit control pagination (max 100).
    Requires USPTO_API_KEY.
    """
    if not USPTO_API_KEY:
        return "Error: USPTO_API_KEY is required. Register at developer.uspto.gov."

    body = _odp_search_body(
        q=query if query else "",
        offset=offset,
        limit=limit,
        sort_field="interferenceMetaData.interferenceLastModifiedDate",
        sort_order="Desc",
    )

    url = f"{ODP_BASE_URL}/api/v1/patent/interferences/decisions/search"
    headers = _odp_headers()

    try:
        result = await _http_post_json(url, headers, body)
        if _is_html(result):
            return "Error: API returned HTML. The interferences API may be temporarily unavailable."
        if isinstance(result, dict):
            return _truncate_json(result)
        return str(result)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            return "Error: USPTO API returned 403 Forbidden. Check your USPTO_API_KEY."
        return f"Interferences error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error searching interferences: {str(e)}"


# ============================================================
# TOOL 16: Patent Application Detail (ODP v2 — GET)
# ============================================================
@mcp.tool()
async def patent_application_detail(
    application_number: str,
    section: str = "",
) -> str:
    """Get detailed data for a specific section of a patent application.

    application_number: e.g. "14876062" (no slashes/commas).
    section: one of "" (full record), "meta-data", "adjustment", "assignment",
             "attorney", "continuity", "foreign-priority", "transactions",
             "documents", "associated-documents".

    Requires USPTO_API_KEY.
    """
    if not USPTO_API_KEY:
        return "Error: USPTO_API_KEY is required. Register at developer.uspto.gov."

    valid_sections = (
        "", "meta-data", "adjustment", "assignment", "attorney",
        "continuity", "foreign-priority", "transactions",
        "documents", "associated-documents",
    )
    if section not in valid_sections:
        return f"Error: section must be one of {valid_sections}, got '{section}'"

    clean = application_number.replace("/", "").replace(",", "").replace(" ", "")

    if section:
        url = f"{ODP_BASE_URL}/api/v1/patent/applications/{clean}/{section}"
    else:
        url = f"{ODP_BASE_URL}/api/v1/patent/applications/{clean}"

    headers = _odp_headers()

    try:
        result = await _http_get(url, headers)
        if _is_html(result):
            return "Error: API returned HTML instead of JSON. The API may be temporarily unavailable."
        if isinstance(result, dict):
            return _truncate_json(result)
        return str(result)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            return "Error: USPTO API returned 403 Forbidden. Check your USPTO_API_KEY."
        if e.response.status_code == 404:
            return f"No data found for application {application_number} section '{section}'"
        return f"USPTO API error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error: {str(e)}"


# ============================================================
# TOOL 17: Patent Status Codes (ODP v2 — POST)
# ============================================================
@mcp.tool()
async def patent_status_codes(
    query: str = "",
    offset: int = 0,
    limit: int = 25,
) -> str:
    """Search patent application status codes and descriptions.

    query can be a keyword or status code number. Leave empty to browse all codes.
    offset and limit control pagination (max 100).
    Requires USPTO_API_KEY.
    """
    if not USPTO_API_KEY:
        return "Error: USPTO_API_KEY is required. Register at developer.uspto.gov."

    body = _odp_search_body(
        q=query if query else None,
        offset=offset,
        limit=limit,
    )

    url = f"{ODP_BASE_URL}/api/v1/patent/status-codes"
    headers = _odp_headers()

    try:
        result = await _http_post_json(url, headers, body)
        if _is_html(result):
            return "Error: API returned HTML instead of JSON. The API may be temporarily unavailable."
        if isinstance(result, dict):
            return _truncate_json(result)
        return str(result)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            return "Error: USPTO API returned 403 Forbidden. Check your USPTO_API_KEY."
        return f"Status codes error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error searching status codes: {str(e)}"


# ============================================================
# TOOL 18: PTAB Trial Decisions Search (ODP v2 — POST)
# ============================================================
@mcp.tool()
async def ptab_trial_decisions_search(
    query: str = "",
    offset: int = 0,
    limit: int = 25,
) -> str:
    """Search PTAB trial decision documents.

    query can be a keyword, trial number (e.g. IPR2023-00123), or patent number.
    Leave empty to browse recent decisions.
    offset and limit control pagination (max 100).
    Requires USPTO_API_KEY.
    """
    if not USPTO_API_KEY:
        return "Error: USPTO_API_KEY is required. Register at developer.uspto.gov."

    body = _odp_search_body(
        q=query if query else "",
        offset=offset,
        limit=limit,
    )

    url = f"{ODP_BASE_URL}/api/v1/patent/trials/decisions/search"
    headers = _odp_headers()

    try:
        result = await _http_post_json(url, headers, body)
        if _is_html(result):
            return "Error: API returned HTML. The PTAB decisions API may be temporarily unavailable."
        if isinstance(result, dict):
            return _truncate_json(result)
        return str(result)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            return "Error: USPTO API returned 403 Forbidden. Check your USPTO_API_KEY."
        return f"PTAB decisions error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error searching PTAB decisions: {str(e)}"


# ============================================================
# TOOL 19: PTAB Trial Documents Search (ODP v2 — POST)
# ============================================================
@mcp.tool()
async def ptab_trial_documents_search(
    query: str = "",
    offset: int = 0,
    limit: int = 25,
) -> str:
    """Search PTAB trial documents filed in proceedings.

    query can be a keyword, trial number (e.g. IPR2023-00123), or document type.
    Leave empty to browse recent documents.
    offset and limit control pagination (max 100).
    Requires USPTO_API_KEY.
    """
    if not USPTO_API_KEY:
        return "Error: USPTO_API_KEY is required. Register at developer.uspto.gov."

    body = _odp_search_body(
        q=query if query else "",
        offset=offset,
        limit=limit,
    )

    url = f"{ODP_BASE_URL}/api/v1/patent/trials/documents/search"
    headers = _odp_headers()

    try:
        result = await _http_post_json(url, headers, body)
        if _is_html(result):
            return "Error: API returned HTML. The PTAB documents API may be temporarily unavailable."
        if isinstance(result, dict):
            return _truncate_json(result)
        return str(result)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            return "Error: USPTO API returned 403 Forbidden. Check your USPTO_API_KEY."
        return f"PTAB documents error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error searching PTAB documents: {str(e)}"


# ============================================================
# TOOL 20: PTAB Detail (ODP v2 — GET)
# ============================================================
@mcp.tool()
async def ptab_detail(
    identifier: str,
    resource_type: str = "proceeding",
) -> str:
    """Look up a single PTAB record by its identifier.

    identifier: the trial number, document ID, appeal number, or interference number.
    resource_type determines the endpoint:
      - "proceeding": GET /api/v1/patent/trials/proceedings/{trialNumber}
      - "decision": GET /api/v1/patent/trials/decisions/{documentIdentifier}
      - "document": GET /api/v1/patent/trials/documents/{documentIdentifier}
      - "appeal": GET /api/v1/patent/appeals/decisions/{documentIdentifier}
      - "appeal_by_number": GET /api/v1/patent/appeals/{appealNumber}/decisions
      - "interference": GET /api/v1/patent/interferences/decisions/{documentIdentifier}
      - "interference_by_number": GET /api/v1/patent/interferences/{interferenceNumber}/decisions
      - "trial_decisions": GET /api/v1/patent/trials/{trialNumber}/decisions
      - "trial_documents": GET /api/v1/patent/trials/{trialNumber}/documents
      - "petition": GET /api/v1/patent/decisions/{petitionDecisionRecordIdentifier}

    Requires USPTO_API_KEY.
    """
    if not USPTO_API_KEY:
        return "Error: USPTO_API_KEY is required. Register at developer.uspto.gov."

    path_map = {
        "proceeding": f"/api/v1/patent/trials/proceedings/{identifier}",
        "decision": f"/api/v1/patent/trials/decisions/{identifier}",
        "document": f"/api/v1/patent/trials/documents/{identifier}",
        "appeal": f"/api/v1/patent/appeals/decisions/{identifier}",
        "appeal_by_number": f"/api/v1/patent/appeals/{identifier}/decisions",
        "interference": f"/api/v1/patent/interferences/decisions/{identifier}",
        "interference_by_number": f"/api/v1/patent/interferences/{identifier}/decisions",
        "trial_decisions": f"/api/v1/patent/trials/{identifier}/decisions",
        "trial_documents": f"/api/v1/patent/trials/{identifier}/documents",
        "petition": f"/api/v1/patent/decisions/{identifier}",
    }

    if resource_type not in path_map:
        return f"Error: resource_type must be one of {list(path_map.keys())}, got '{resource_type}'"

    url = f"{ODP_BASE_URL}{path_map[resource_type]}"
    headers = _odp_headers()

    try:
        result = await _http_get(url, headers)
        if _is_html(result):
            return "Error: API returned HTML instead of JSON. The API may be temporarily unavailable."
        if isinstance(result, dict):
            return _truncate_json(result)
        return str(result)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            return "Error: USPTO API returned 403 Forbidden. Check your USPTO_API_KEY."
        if e.response.status_code == 404:
            return f"No {resource_type} found for identifier '{identifier}'"
        return f"USPTO API error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error: {str(e)}"


# ============================================================
# Run the server
# ============================================================
if __name__ == "__main__":
    mcp.run(transport="stdio")
