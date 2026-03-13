"""
USPTO MCP Server - Model Context Protocol server for the USPTO APIs.

Provides tools for:
- Trademark status lookup (TSDR API)
- Trademark document retrieval
- Multi-case trademark status
- USPTO dataset search (DS-API)
- Patent/Trademark data field listing
"""

import os
import json
import logging
import httpx
from typing import Any, Optional
from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uspto-mcp-server")

# --- Configuration ---
USPTO_API_KEY = os.environ.get("USPTO_API_KEY", "")
TSDR_BASE_URL = "https://tsdrapi.uspto.gov"
DS_API_BASE_URL = "https://developer.uspto.gov/ds-api"
ODP_BASE_URL = "https://data.uspto.gov"

# Rate limit: 60 req/min for TSDR, 4 req/min for PDF/ZIP downloads

# --- Initialize MCP Server ---
mcp = FastMCP("USPTO")


def _tsdr_headers() -> dict:
    """Common headers for TSDR API requests."""
    headers = {"Accept": "application/json"}
    if USPTO_API_KEY:
        headers["USPTO-API-KEY"] = USPTO_API_KEY
    return headers


def _ds_api_headers() -> dict:
    """Common headers for DS-API requests."""
    return {"Accept": "application/json"}


async def _http_get(url: str, headers: dict, params: dict | None = None) -> dict | str:
    """Perform an HTTP GET request and return parsed JSON or text."""
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        resp = await client.get(url, headers=headers, params=params)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        if "json" in content_type:
            return resp.json()
        elif "xml" in content_type:
            return resp.text
        else:
            # Try JSON first, fall back to text
            try:
                return resp.json()
            except Exception:
                return resp.text


async def _http_post(url: str, headers: dict, data: dict) -> dict | str:
    """Perform an HTTP POST request with form data."""
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        resp = await client.post(url, headers=headers, data=data)
        resp.raise_for_status()
        try:
            return resp.json()
        except Exception:
            return resp.text


# ============================================================
# TOOL 1: Trademark Case Status
# ============================================================
@mcp.tool()
async def trademark_status(
    case_id: str,
    id_type: str = "sn",
) -> str:
    """
    Look up the status of a US trademark application or registration.

    Args:
        case_id: The case identifier number (e.g., "97123456" for serial number, "1234567" for registration number).
        id_type: Type of identifier. One of: "sn" (serial number, default), "rn" (registration number), "ref" (reference number), "ir" (international registration).

    Returns:
        Trademark case status information in XML format including filing date, status, mark text, owner info, etc.
    """
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
    case_ids: list[str],
    id_type: str = "sn",
) -> str:
    """
    Look up the status of multiple trademark cases at once.

    Args:
        case_ids: List of case identifier numbers (e.g., ["97123456", "97654321"]).
        id_type: Type of identifiers. One of: "sn" (serial number, default), "rn" (registration number), "ref" (reference number), "ir" (international registration).

    Returns:
        JSON with status details for all requested trademark cases.
    """
    if not USPTO_API_KEY:
        return "Error: USPTO_API_KEY environment variable is not set."

    valid_types = ("sn", "rn", "ref", "ir")
    if id_type not in valid_types:
        return f"Error: id_type must be one of {valid_types}"

    url = f"{TSDR_BASE_URL}/ts/cd/caseMultiStatus/{id_type}"
    headers = _tsdr_headers()
    params = {"ids": ",".join(case_ids)}

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
    """
    List all prosecution documents for a trademark case.

    Args:
        case_id: The case identifier number.
        id_type: Type of identifier. One of: "sn" (serial number, default), "rn" (registration number), "ref" (reference number), "ir" (international registration).

    Returns:
        XML listing of all documents filed for the trademark case including document IDs, types, and dates.
    """
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
    """
    Check when a trademark case was last updated in the prosecution history.

    Args:
        serial_number: The US serial number of the trademark application (e.g., "97123456").

    Returns:
        JSON with the last update timestamp for the trademark prosecution history.
    """
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
# TOOL 5: List USPTO Datasets
# ============================================================
@mcp.tool()
async def list_datasets() -> str:
    """
    List all available USPTO data sets that can be searched.

    Returns:
        JSON list of available datasets with their API keys, versions, and documentation URLs.
    """
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
# TOOL 6: List Dataset Fields
# ============================================================
@mcp.tool()
async def list_dataset_fields(
    dataset: str = "oa_citations",
    version: str = "v1",
) -> str:
    """
    List the searchable fields for a specific USPTO dataset.

    Args:
        dataset: The dataset name (e.g., "oa_citations"). Use list_datasets() to see available datasets.
        version: The dataset version (e.g., "v1").

    Returns:
        JSON list of field names that can be used in search queries.
    """
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
# TOOL 7: Search USPTO Dataset
# ============================================================
@mcp.tool()
async def search_dataset(
    query: str,
    dataset: str = "oa_citations",
    version: str = "v1",
    start: int = 0,
    rows: int = 25,
) -> str:
    """
    Search a USPTO dataset using Lucene query syntax.

    Args:
        query: Search query in Lucene syntax (e.g., "patent_title:artificial AND patent_title:intelligence"). Use "*:*" to match all records.
        dataset: The dataset name (e.g., "oa_citations"). Use list_datasets() to see available datasets.
        version: The dataset version (e.g., "v1").
        start: Starting record offset for pagination (default 0).
        rows: Number of records to return (default 25, max 100).

    Returns:
        JSON array of matching records from the dataset.
    """
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
        result = await _http_post(url, headers, data)
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
# TOOL 8: ODP Patent Search
# ============================================================
@mcp.tool()
async def patent_search(
    query: str,
    start: int = 0,
    rows: int = 25,
) -> str:
    """
    Search for US patents on the USPTO Open Data Portal.

    Args:
        query: Search query (e.g., "artificial intelligence", patent number like "11123456", or inventor name).
        start: Starting record offset for pagination (default 0).
        rows: Number of records to return (default 25).

    Returns:
        JSON with matching patent records including patent numbers, titles, inventors, assignees, and filing dates.
    """
    url = f"{ODP_BASE_URL}/api/v1/patent/applications/search"
    headers = {"Accept": "application/json"}
    if USPTO_API_KEY:
        headers["X-API-KEY"] = USPTO_API_KEY
    params = {
        "query": query,
        "start": start,
        "rows": rows,
    }

    try:
        result = await _http_get(url, headers, params)
        if isinstance(result, dict):
            return json.dumps(result, indent=2)
        return str(result)
    except httpx.HTTPStatusError as e:
        return f"ODP patent search error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error searching patents: {str(e)}"


# ============================================================
# TOOL 9: ODP Bulk Data Products
# ============================================================
@mcp.tool()
async def list_bulk_data_products(
    search_query: str = "",
) -> str:
    """
    List available USPTO bulk data products for download.

    Args:
        search_query: Optional search term to filter products (e.g., "Grants", "Trademarks"). Leave empty for all products.

    Returns:
        JSON list of available bulk data products with titles, descriptions, and download information.
    """
    url = f"{ODP_BASE_URL}/api/v1/datasets/products/search"
    headers = {"Accept": "application/json"}
    if USPTO_API_KEY:
        headers["X-API-KEY"] = USPTO_API_KEY

    params: dict[str, Any] = {"latest": "true"}
    if search_query:
        params["productTitle"] = search_query

    try:
        result = await _http_get(url, headers, params)
        if isinstance(result, dict):
            return json.dumps(result, indent=2)
        return str(result)
    except httpx.HTTPStatusError as e:
        return f"ODP error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error: {str(e)}"


# ============================================================
# TOOL 10: PTAB Proceedings Search
# ============================================================
@mcp.tool()
async def ptab_search(
    query: str,
    start: int = 0,
    rows: int = 25,
) -> str:
    """
    Search Patent Trial and Appeal Board (PTAB) proceedings.

    Args:
        query: Search query for PTAB proceedings (e.g., patent number, party name, proceeding number like "IPR2023-00123").
        start: Starting record offset for pagination (default 0).
        rows: Number of records to return (default 25).

    Returns:
        JSON with matching PTAB proceedings including proceeding numbers, types (IPR, PGR, CBM), parties, patent info, and status.
    """
    url = f"{ODP_BASE_URL}/api/v1/patent/trials/proceedings/search"
    headers = {"Accept": "application/json"}
    if USPTO_API_KEY:
        headers["X-API-KEY"] = USPTO_API_KEY
    params = {
        "query": query,
        "start": start,
        "rows": rows,
    }

    try:
        result = await _http_get(url, headers, params)
        if isinstance(result, dict):
            return json.dumps(result, indent=2)
        return str(result)
    except httpx.HTTPStatusError as e:
        return f"PTAB search error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Error searching PTAB: {str(e)}"


# ============================================================
# Run the server
# ============================================================
if __name__ == "__main__":
    mcp.run(transport="stdio")
