# USPTO Open Data Portal (ODP) — Complete API Reference

> Compiled from official USPTO documentation: PEDS-to-ODP Mapping, ODP API Query Spec, and patent-data-schema.json.
> Base URL: `https://api.uspto.gov`
> Authentication: `X-API-KEY` header (obtain from My ODP at data.uspto.gov)
> Date: 2026-03-15

---

## Table of Contents
1. [Authentication](#authentication)
2. [Patent File Wrapper Search](#patent-file-wrapper-search)
3. [Application Data Lookup](#application-data-lookup)
4. [Document Metadata & Download](#document-metadata--download)
5. [Bulk Data Products](#bulk-data-products)
6. [PTAB Trials](#ptab-trials)
7. [Query Syntax Reference](#query-syntax-reference)
8. [Key Searchable Fields](#key-searchable-fields)

---

## Authentication

All ODP API requests require an API key passed via header:

```
X-API-KEY: <your-api-key>
```

Obtain your key:
1. Create a USPTO account at https://account.uspto.gov
2. Link ID.me verification
3. Access your key at My ODP page on https://data.uspto.gov

---

## Patent File Wrapper Search

### GET Search
```
GET /api/v1/patent/applications/search
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `q` | string | Search query (free-form or field:value DSL) |
| `filters` | string | Field-value filter (`fieldName%20value`) |
| `rangeFilters` | string | Range filter (`fieldName%20from:to`) |
| `sort` | string | Sort order (`fieldName%20asc/desc`) |
| `fields` | string | Comma-separated list of fields to return |
| `offset` | int | Starting position (default: 0) |
| `limit` | int | Number of results (default: 25) |

**Examples:**

```
# Search by patent number
GET /api/v1/patent/applications/search?q=applicationMetaData.patentNumber:9524132

# Search by application number (no slashes/commas)
GET /api/v1/patent/applications/search?q=applicationNumberText:14876062

# Search by inventor
GET /api/v1/patent/applications/search?q=applicationMetaData.inventorBag.inventorNameText:Googl*

# Search by applicant
GET /api/v1/patent/applications/search?q=applicationMetaData.firstApplicantName:Nordisk

# Search by title (quoted phrase)
GET /api/v1/patent/applications/search?q=applicationMetaData.inventionTitle:%22ink%20jet%20printer%22

# Date range in q
GET /api/v1/patent/applications/search?q=applicationMetaData.filingDate:[2024-01-01%20TO%202024-08-30]

# Status filter
GET /api/v1/patent/applications/search?q=applicationMetaData.applicationStatusDescriptionText:%22Patented%20Case%22

# Combined AND
GET /api/v1/patent/applications/search?q=applicationMetaData.applicationTypeLabelName:Utility%20AND%20applicationMetaData.entityStatusData.businessEntityStatusCategory:Small

# Wildcard
GET /api/v1/patent/applications/search?q=applicationMetaData.firstApplicantName:Technolog*

# With filters (separate param)
GET /api/v1/patent/applications/search?filters=applicationMetaData.applicationTypeCode%20UTL

# With range filter
GET /api/v1/patent/applications/search?rangeFilters=applicationMetaData.grantDate%202010-01-01%3A2011-01-01

# With sort
GET /api/v1/patent/applications/search?sort=applicationMetaData.applicationStatusDate%20asc

# Limit response fields
GET /api/v1/patent/applications/search?fields=applicationNumberText%2CapplicationMetaData.patentNumber%2CapplicationMetaData.applicationTypeCode

# Pagination
GET /api/v1/patent/applications/search?offset=10&limit=50
```

### POST Search (More Powerful)
```
POST /api/v1/patent/applications/search
Content-Type: application/json
```

**Full request body (all optional):**
```json
{
  "q": "applicationMetaData.applicationTypeLabelName:Utility",
  "filters": [
    {
      "name": "applicationMetaData.applicationStatusDescriptionText",
      "value": ["Patented Case"]
    }
  ],
  "rangeFilters": [
    {
      "field": "applicationMetaData.grantDate",
      "valueFrom": "2010-08-04",
      "valueTo": "2022-08-04"
    }
  ],
  "sort": [
    {
      "field": "applicationMetaData.filingDate",
      "order": "desc"
    }
  ],
  "fields": [
    "applicationNumberText",
    "correspondenceAddressBag",
    "applicationMetaData.filingDate"
  ],
  "pagination": {
    "offset": 0,
    "limit": 25
  },
  "facets": [
    "applicationMetaData.applicationTypeLabelName",
    "applicationMetaData.applicationStatusCode"
  ]
}
```

**Minimal valid POST (empty body = default search):**
```json
{}
```

### Download Search Results
```
GET /api/v1/patent/applications/search/download
```
Same parameters as search. Max 6MB response.

---

## Application Data Lookup

### Get Application by Number
```
GET /api/v1/patent/applications/{applicationNumberText}/
```
Returns full application record. `applicationNumberText` = digits only (no slashes).

**Example:**
```
GET /api/v1/patent/applications/14876062/
```

---

## Document Metadata & Download

### List Documents for an Application
```
GET /api/v1/patent/applications/{applicationNumberText}/documents
```

**Response includes:**
```json
{
  "applicationNumberText": "16123123",
  "officialDate": "2020-08-28T17:17:43.000-0400",
  "documentIdentifier": "KEEQMGWJLDFLYX4",
  "documentCode": "APP.FILE.REC",
  "documentCodeDescriptionText": "Filing Receipt",
  "directionCategory": "OUTGOING",
  "downloadOptionBag": [
    {
      "mimeTypeIdentifier": "PDF",
      "downloadUrl": "https://api.uspto.gov/api/v1/download/applications/16123123/KEEQMGWJLDFLYX4.pdf",
      "pageTotalQuantity": 4
    }
  ]
}
```

### Download a Document
```
GET /api/v1/download/applications/{applicationNumberText}/{documentIdentifier}.pdf
```
Requires `X-API-KEY` header.

---

## Bulk Data Products

### Full Data Download
```
GET /api/v1/datasets/products/PTFWPRE
```
Weekly full patent file wrapper datasets (released Mondays).

### Daily Delta
```
GET /api/v1/datasets/products/PTFWPRD
```
Daily incremental updates.

**Response example:**
```json
{
  "fileName": "patent-filewrapper-delta-friday-json.zip",
  "fileSize": 153702753,
  "fileDataFromDate": "2025-01-24",
  "fileDataToDate": "2025-01-24",
  "fileDownloadURI": "https://beta-api.uspto.gov/api/v1/datasets/products/files/PTFWPRD/patent-filewrapper-delta-friday-json.zip"
}
```

---

## PTAB Trials

### Search Proceedings
```
GET /api/v1/patent/trials/proceedings/search?q={query}
```

### Search Decisions
```
GET /api/v1/patent/trials/decisions/search?q={query}
```

### Search Documents
```
GET /api/v1/patent/trials/documents/search?q={query}
```

All support the same `q`, `filters`, `rangeFilters`, `sort`, `fields`, `offset`, `limit` parameters.

---

## Query Syntax Reference

### Operators in `q` Parameter

| Operator | Syntax | Example |
|----------|--------|---------|
| Free-form | `q=keyword` | `q=Utility` |
| Field search | `q=field:value` | `q=applicationMetaData.patentNumber:9524132` |
| AND | `q=A AND B` | `q=Patented%20AND%20Design` |
| OR | `q=A OR B` | `q=Small%20OR%20Micro` |
| NOT | `q=A NOT B` | `q=%22Patented%20Case%22%20NOT%20Design` |
| Phrase | `q="exact phrase"` | `q=%22Patented%20Case%22` |
| Wildcard (*) | `q=prefix*` | `q=Technolog*` |
| Wildcard (?) | `q=te?t` | `q=ANDERS?N` |
| Range (numbers) | `q=field:[min TO max]` | `q=applicationMetaData.applicationConfirmationNumber:[2700%20TO%202710]` |
| Range (dates) | `q=field:[date1 TO date2]` | `q=applicationMetaData.filingDate:[2024-01-01%20TO%202024-08-30]` |
| Greater/Less | `q=field:>=value` | `q=applicationMetaData.applicationStatusDate:>=2024-02-20` |
| Multi-value OR | `q=field:(A OR B)` | `q=applicationMetaData.applicationTypeLabelName:(Design%20OR%20Plant)` |

### Filters Parameter (GET)
```
filters=fieldName%20value
```
Multiple filters: `&filters=field1%20value1&filters=field2%20value2`
Multi-value: `filters=fieldName%20value1%2Cvalue2`

### Range Filters (GET)
```
rangeFilters=fieldName%20fromValue%3AtoValue
```
Colon (`:` = `%3A`) separates from/to.

### Sort (GET)
```
sort=fieldName%20asc
sort=fieldName%20desc
```
Multiple: `&sort=field1%20asc&sort=field2%20desc`

---

## Key Searchable Fields

### Application-Level
| Field | Description |
|-------|-------------|
| `applicationNumberText` | Application number (digits only, e.g. "14876062") |
| `applicationMetaData.patentNumber` | Granted patent number |
| `applicationMetaData.inventionTitle` | Title of invention |
| `applicationMetaData.filingDate` | Filing date (YYYY-MM-DD) |
| `applicationMetaData.grantDate` | Grant date |
| `applicationMetaData.applicationStatusDescriptionText` | Status (e.g. "Patented Case") |
| `applicationMetaData.applicationStatusCode` | Numeric status code |
| `applicationMetaData.applicationStatusDate` | Date of current status |
| `applicationMetaData.applicationTypeLabelName` | Type: Utility, Design, Plant, Re-Issue |
| `applicationMetaData.applicationTypeCode` | Type code: UTL, DES, PLT, etc. |
| `applicationMetaData.firstApplicantName` | First named applicant |
| `applicationMetaData.examinerNameText` | Examiner name |
| `applicationMetaData.groupArtUnitNumber` | Art unit |
| `applicationMetaData.applicationConfirmationNumber` | Confirmation number |

### Entity Status
| Field | Description |
|-------|-------------|
| `applicationMetaData.entityStatusData.businessEntityStatusCategory` | Small, Micro, Regular Undiscounted |

### Inventor Data
| Field | Description |
|-------|-------------|
| `applicationMetaData.inventorBag.inventorNameText` | Inventor full name |
| `applicationMetaData.inventorBag.firstName` | Inventor first name |
| `applicationMetaData.inventorBag.lastName` | Inventor last name |

### Prosecution History Events
| Field | Description |
|-------|-------------|
| `eventDataBag.eventCode` | Event code |
| `eventDataBag.eventDescriptionText` | Event description |
| `eventDataBag.eventDate` | Event date |

### Continuity Data
| Field | Description |
|-------|-------------|
| `parentContinuityBag` | Parent applications |
| `childContinuityBag` | Child/continuation applications |

### Correspondence
| Field | Description |
|-------|-------------|
| `correspondenceAddressBag` | Correspondence address data |

### Other Flags
| Field | Description |
|-------|-------------|
| `applicationMetaData.firstInventorToFileIndicator` | AIA first-to-file flag (Y/N) |

---

## Important Notes

1. **All parameters are optional** — even an empty POST `{}` is valid
2. **Field names are case-sensitive**
3. **Text fields cannot be used for sorting**
4. **URL encoding required for GET requests** — space = `%20`, colon = `%3A`, quote = `%22`
5. **Pagination defaults**: offset=0, limit=25
6. **Schema reference**: Full 274-field schema at `https://data.uspto.gov/documents/documents/patent-data-schema.json`
7. **Rate limits**: Not explicitly documented; be respectful

---

## Source Documents
- PEDS-to-ODP API Mapping: `https://data.uspto.gov/documents/documents/PEDS-to-ODP-API-Mapping.pdf`
- ODP API Query Spec: `https://data.uspto.gov/documents/documents/ODP-API-Query-Spec.pdf`
- Patent Data Schema: `https://data.uspto.gov/documents/documents/patent-data-schema.json`
- Getting Started: `https://data.uspto.gov/apis/getting-started`
- Swagger UI: `https://data.uspto.gov/swagger/index.html`
