![Swagger UI](https://data.uspto.gov/swagger/logo-small.png)Explore

## Open Data Portal (ODP) API  ```  1.0.0  ```    ``` OAS 3.0 ```

[https://data.uspto.gov/swagger/swagger.yaml](https://data.uspto.gov/swagger/swagger.yaml)

The Open Data Portal (ODP) API allows you to extract USPTO data at no cost - with several ways to do it. To learn about the ODP API Rate Limits, please visit to the [API Rate Limits page](https://data.uspto.gov/apis/api-rate-limits).

**Before proceeding**, you must have an ODP API key in order to access these Swagger UI resources. Once you have obtained an API key, you can pass the API key into a REST API call in the x-api-key header of the request. For more details and steps to generate an API key visit to the [Getting Started page](https://data.uspto.gov/apis/getting-started).

For example, the request to access patent data for an application might look like as below.

`curl -X "GET" "https://api.uspto.gov/api/v1/patent/applications/14412875" -H "X-API-KEY:YOUR_API_KEY"`

`curl -X "POST" "https://api.uspto.gov/api/v1/patent/applications/search" -H "X-API-KEY:YOUR_API_KEY" -d "{\"q\":\"applicationMetaData.applicationTypeLabelName:Utility\"}"
`

[USPTO - Website](https://data.uspto.gov/apis/getting-started)

[Send email to USPTO](mailto:data@uspto.gov)

Servers

https://api.uspto.gov

Authorize

#### [Patent Search](https://data.uspto.gov/swagger/index.html\#/Patent%20Search)    Search patent data by supplying query parameter or json request. Get data of a specific application or a section of an application

POST[/api/v1/patent/applications/search](https://data.uspto.gov/swagger/index.html#/Patent%20Search/post_api_v1_patent_applications_search)
Search patent applications by supplying json payload

GET[/api/v1/patent/applications/search](https://data.uspto.gov/swagger/index.html#/Patent%20Search/get_api_v1_patent_applications_search)
Patent application search by supplying query parameters

POST[/api/v1/patent/applications/search/download](https://data.uspto.gov/swagger/index.html#/Patent%20Search/post_api_v1_patent_applications_search_download)
Download patent data by supplying json payload

GET[/api/v1/patent/applications/search/download](https://data.uspto.gov/swagger/index.html#/Patent%20Search/get_api_v1_patent_applications_search_download)
Patent application search by supplying query parameters

GET[/api/v1/patent/applications/{applicationNumberText}](https://data.uspto.gov/swagger/index.html#/Patent%20Search/get_api_v1_patent_applications__applicationNumberText_)
Patent application data for a provided application number

GET[/api/v1/patent/applications/{applicationNumberText}/meta-data](https://data.uspto.gov/swagger/index.html#/Patent%20Search/get_api_v1_patent_applications__applicationNumberText__meta_data)
Get patent application meta data

GET[/api/v1/patent/applications/{applicationNumberText}/adjustment](https://data.uspto.gov/swagger/index.html#/Patent%20Search/get_api_v1_patent_applications__applicationNumberText__adjustment)
Get patent term adjustment data for an application number

GET[/api/v1/patent/applications/{applicationNumberText}/assignment](https://data.uspto.gov/swagger/index.html#/Patent%20Search/get_api_v1_patent_applications__applicationNumberText__assignment)
Get patent assignment data for an application number

GET[/api/v1/patent/applications/{applicationNumberText}/attorney](https://data.uspto.gov/swagger/index.html#/Patent%20Search/get_api_v1_patent_applications__applicationNumberText__attorney)
Get attorney/agent data for an application number

GET[/api/v1/patent/applications/{applicationNumberText}/continuity](https://data.uspto.gov/swagger/index.html#/Patent%20Search/get_api_v1_patent_applications__applicationNumberText__continuity)
Get continuity data for an application number

GET[/api/v1/patent/applications/{applicationNumberText}/foreign-priority](https://data.uspto.gov/swagger/index.html#/Patent%20Search/get_api_v1_patent_applications__applicationNumberText__foreign_priority)
Get foreign-priority data for an application number

GET[/api/v1/patent/applications/{applicationNumberText}/transactions](https://data.uspto.gov/swagger/index.html#/Patent%20Search/get_api_v1_patent_applications__applicationNumberText__transactions)
Get transaction data for an application number

GET[/api/v1/patent/applications/{applicationNumberText}/documents](https://data.uspto.gov/swagger/index.html#/Patent%20Search/get_api_v1_patent_applications__applicationNumberText__documents)
Documents details for an application number

GET[/api/v1/patent/applications/{applicationNumberText}/associated-documents](https://data.uspto.gov/swagger/index.html#/Patent%20Search/get_api_v1_patent_applications__applicationNumberText__associated_documents)
Associated (pgpub, grant) documents meta-data for an application

POST[/api/v1/patent/status-codes](https://data.uspto.gov/swagger/index.html#/Patent%20Search/post_api_v1_patent_status_codes)
Search patent application status codes and status code description

GET[/api/v1/patent/status-codes](https://data.uspto.gov/swagger/index.html#/Patent%20Search/get_api_v1_patent_status_codes)
Search patent application status codes and status code description

#### [Bulk DataSets](https://data.uspto.gov/swagger/index.html\#/Bulk%20DataSets)    Bulk Dataset Directory provides a single repository for raw public bulk data. It contains research data from the office of the Chief Economist.

GET[/api/v1/datasets/products/search](https://data.uspto.gov/swagger/index.html#/Bulk%20DataSets/get_api_v1_datasets_products_search)
Search bulk datasets products by supplying query parameters

GET[/api/v1/datasets/products/{productIdentifier}](https://data.uspto.gov/swagger/index.html#/Bulk%20DataSets/get_api_v1_datasets_products__productIdentifier_)
Bulk data- find a product by its identifier (shortName)

GET[/api/v1/datasets/products/files/{productIdentifier}/{fileName}](https://data.uspto.gov/swagger/index.html#/Bulk%20DataSets/get_api_v1_datasets_products_files__productIdentifier___fileName_)
Download bulk data product file

#### [Petition Decision Search](https://data.uspto.gov/swagger/index.html\#/Petition%20Decision%20Search)    Petition Decision Search

POST[/api/v1/petition/decisions/search](https://data.uspto.gov/swagger/index.html#/Petition%20Decision%20Search/post_api_v1_petition_decisions_search)
Search petition decision applications by supplying json payload

GET[/api/v1/petition/decisions/search](https://data.uspto.gov/swagger/index.html#/Petition%20Decision%20Search/get_api_v1_petition_decisions_search)
Petition decision application search by supplying query parameters

POST[/api/v1/petition/decisions/search/download](https://data.uspto.gov/swagger/index.html#/Petition%20Decision%20Search/post_api_v1_petition_decisions_search_download)
Download petition decision data by supplying json payload

GET[/api/v1/petition/decisions/search/download](https://data.uspto.gov/swagger/index.html#/Petition%20Decision%20Search/get_api_v1_petition_decisions_search_download)
Petition decision application search by supplying query parameters

GET[/api/v1/petition/decisions/{petitionDecisionRecordIdentifier}](https://data.uspto.gov/swagger/index.html#/Petition%20Decision%20Search/get_api_v1_petition_decisions__petitionDecisionRecordIdentifier_)
Petition decision application data for a provided application number

#### [PTAB Trials](https://data.uspto.gov/swagger/index.html\#/PTAB%20Trials)    PTAB Trials APIs: proceedings, documents and decisions.

#### [Proceedings](https://data.uspto.gov/swagger/index.html\#/Proceedings)    All public PTAB Trial proceedings

POST[/api/v1/patent/trials/proceedings/search](https://data.uspto.gov/swagger/index.html#/Proceedings/post_api_v1_patent_trials_proceedings_search)
Search trials proceedings using json payload

GET[/api/v1/patent/trials/proceedings/search](https://data.uspto.gov/swagger/index.html#/Proceedings/get_api_v1_patent_trials_proceedings_search)
Search trials proceedings using query parameters

POST[/api/v1/patent/trials/proceedings/search/download](https://data.uspto.gov/swagger/index.html#/Proceedings/post_api_v1_patent_trials_proceedings_search_download)
Download trials proceedings search results in json or csv format using json payload

GET[/api/v1/patent/trials/proceedings/search/download](https://data.uspto.gov/swagger/index.html#/Proceedings/get_api_v1_patent_trials_proceedings_search_download)
Download trials proceedings search results in json or csv format using query parameters

GET[/api/v1/patent/trials/proceedings/{trialNumber}](https://data.uspto.gov/swagger/index.html#/Proceedings/get_api_v1_patent_trials_proceedings__trialNumber_)
Retrieve a single trials proceeding by trial number

#### [Decisions](https://data.uspto.gov/swagger/index.html\#/Decisions)    All public decisions filed in PTAB Trials

POST[/api/v1/patent/trials/decisions/search](https://data.uspto.gov/swagger/index.html#/Decisions/post_api_v1_patent_trials_decisions_search)
Search trials decisions documents using json payload

GET[/api/v1/patent/trials/decisions/search](https://data.uspto.gov/swagger/index.html#/Decisions/get_api_v1_patent_trials_decisions_search)
Search trials decisions documents using query parameters

POST[/api/v1/patent/trials/decisions/search/download](https://data.uspto.gov/swagger/index.html#/Decisions/post_api_v1_patent_trials_decisions_search_download)
Download trials decisions documents search results in json or csv format using json payload

GET[/api/v1/patent/trials/decisions/search/download](https://data.uspto.gov/swagger/index.html#/Decisions/get_api_v1_patent_trials_decisions_search_download)
Download trials decisions documents search results in json or csv format using query parameters

GET[/api/v1/patent/trials/decisions/{documentIdentifier}](https://data.uspto.gov/swagger/index.html#/Decisions/get_api_v1_patent_trials_decisions__documentIdentifier_)
Retrieve a single trials decisions document by document identifier

GET[/api/v1/patent/trials/{trialNumber}/decisions](https://data.uspto.gov/swagger/index.html#/Decisions/get_api_v1_patent_trials__trialNumber__decisions)
Retrieve all trials decisions documents by trial number

#### [Documents](https://data.uspto.gov/swagger/index.html\#/Documents)    All public documents filed in PTAB Trials

POST[/api/v1/patent/trials/documents/search](https://data.uspto.gov/swagger/index.html#/Documents/post_api_v1_patent_trials_documents_search)
Search trials documents using json payload

GET[/api/v1/patent/trials/documents/search](https://data.uspto.gov/swagger/index.html#/Documents/get_api_v1_patent_trials_documents_search)
Search trials documents using query parameters

POST[/api/v1/patent/trials/documents/search/download](https://data.uspto.gov/swagger/index.html#/Documents/post_api_v1_patent_trials_documents_search_download)
Download trials documents search results in json or csv format using json payload

GET[/api/v1/patent/trials/documents/search/download](https://data.uspto.gov/swagger/index.html#/Documents/get_api_v1_patent_trials_documents_search_download)
Download trials document search results in json or csv format using query parameters

GET[/api/v1/patent/trials/documents/{documentIdentifier}](https://data.uspto.gov/swagger/index.html#/Documents/get_api_v1_patent_trials_documents__documentIdentifier_)
Retrieve a single trials document by document identifier

GET[/api/v1/patent/trials/{trialNumber}/documents](https://data.uspto.gov/swagger/index.html#/Documents/get_api_v1_patent_trials__trialNumber__documents)
Retrieve all trials documents by trial number

#### [PTAB Appeals](https://data.uspto.gov/swagger/index.html\#/PTAB%20Appeals)    All public decisions filed in PTAB Appeals

POST[/api/v1/patent/appeals/decisions/search](https://data.uspto.gov/swagger/index.html#/PTAB%20Appeals/post_api_v1_patent_appeals_decisions_search)
Search appeals decisions using json payload

GET[/api/v1/patent/appeals/decisions/search](https://data.uspto.gov/swagger/index.html#/PTAB%20Appeals/get_api_v1_patent_appeals_decisions_search)
Search appeals decisions using query parameters

POST[/api/v1/patent/appeals/decisions/search/download](https://data.uspto.gov/swagger/index.html#/PTAB%20Appeals/post_api_v1_patent_appeals_decisions_search_download)
Download appeals decisions search results in json or csv format using json payload

GET[/api/v1/patent/appeals/decisions/search/download](https://data.uspto.gov/swagger/index.html#/PTAB%20Appeals/get_api_v1_patent_appeals_decisions_search_download)
Download appeals decisions search results in json or csv format using query parameters

GET[/api/v1/patent/appeals/decisions/{documentIdentifier}](https://data.uspto.gov/swagger/index.html#/PTAB%20Appeals/get_api_v1_patent_appeals_decisions__documentIdentifier_)
Retrieve appeals decisions by document Identifier

GET[/api/v1/patent/appeals/{appealNumber}/decisions](https://data.uspto.gov/swagger/index.html#/PTAB%20Appeals/get_api_v1_patent_appeals__appealNumber__decisions)
Retrieve appeals decisions by appeal number

#### [PTAB Interferences](https://data.uspto.gov/swagger/index.html\#/PTAB%20Interferences)    All public decisions filed in PTAB Interferences

POST[/api/v1/patent/interferences/decisions/search](https://data.uspto.gov/swagger/index.html#/PTAB%20Interferences/post_api_v1_patent_interferences_decisions_search)
Search interferences decisions using json payload

GET[/api/v1/patent/interferences/decisions/search](https://data.uspto.gov/swagger/index.html#/PTAB%20Interferences/get_api_v1_patent_interferences_decisions_search)
Search interferences decisions using query parameters

POST[/api/v1/patent/interferences/decisions/search/download](https://data.uspto.gov/swagger/index.html#/PTAB%20Interferences/post_api_v1_patent_interferences_decisions_search_download)
Download interferences decisions search results in json or csv format using json payload

GET[/api/v1/patent/interferences/decisions/search/download](https://data.uspto.gov/swagger/index.html#/PTAB%20Interferences/get_api_v1_patent_interferences_decisions_search_download)
Download interferences decisions search results in json or csv format using query parameters

GET[/api/v1/patent/interferences/{interferenceNumber}/decisions](https://data.uspto.gov/swagger/index.html#/PTAB%20Interferences/get_api_v1_patent_interferences__interferenceNumber__decisions)
Retrieve interferences decisions by interference number

GET[/api/v1/patent/interferences/decisions/{documentIdentifier}](https://data.uspto.gov/swagger/index.html#/PTAB%20Interferences/get_api_v1_patent_interferences_decisions__documentIdentifier_)
Retrieve interferences decisions by document identifier

#### Schemas

PatentSearchRequest

PatentDownloadRequest

PatentDataResponse

ApplicationMetaData

PatentTermAdjustment

Assignment

RecordAttorney

ParentContinuityData

ChildContinuityData

ForeignPriority

EventData

DocumentBag

PGPubFileMetaData

GrantFileMetaData

StatusCodeSearchResponse

BdssResponseProductBag

PetitionDecisionResponseBag

PetitionDecisionIdentifierResponseBag

ProceedingDataResponse

PatentTrialProceedingDataBag

DocumentDataResponse

PatentTrialDocumentDataBag

DecisionDataResponse

PatentTrialDecisionDataBag

InterferenceDecisionDataResponse

AppealDecisionDataResponse

PatentAppealDataBag

q

sort

offset

limit

facets

fields

filters

rangeFilters

format

BadRequest

Forbidden

NotFound

Status413

InternalError