---
jira_issue_type: "Epic"
epic_key: "DXV-FRE"
epic_name: "DXV — Data Exchange Vault — AML Data Ingestion · Feedback (Quarantine Export)"
version: "1.0"
user_story_count: 10
total_test_cases: 62
---

# DXV — Data Exchange Vault — Test Suite Overview

**Module:** AML Data Ingestion · Feedback (Quarantine Export)  
**Pipeline:** `failed-record-export`  |  **Epic Key:** `DXV-FRE`  |  **Version:** 1.0

| Metric | Value |
| --- | --- |
| User Stories | 10 |
| Total Test Cases | 62 |
| Total Test Steps | 175 |
| Author | Software Test Engineering |
| Generated | 2026-06-11 |

## Suite Summary

Integration test suite for the DXV failed-record-export pipeline stage. This stage exports validation failures from Iceberg quarantine tables to MinIO as delimiter-separated files, together with acquisition success / error envelope flag files, using the same data contract and process_date as the wider AML flow. The suite below decomposes the stage into discrete functional and non-functional areas, each captured as an Agile User Story with executable, data-driven test cases.

## In Scope

- Pipeline invocation, parameter resolution and configuration precedence.
- Reading Iceberg quarantine tables and per-table iteration / skip behaviour.
- Output path resolution, normalisation and ORG_UNIT prefixing.
- Generation of the three data exports (clean bad, aggregated, detailed).
- Envelope flag-file semantics (acq_success vs envelope_error).
- Export format, delimiter and header handling (csv/txt/pipe/gs).
- RFFilespec headerless alignment.
- Storage behaviour, .keep markers and *.zip.flag naming conventions.
- Downstream DXV integration and ingest-key alignment.
- Non-functional qualities: performance, reliability, security, compatibility.

## Out of Scope

- Upstream data-validation logic that places rows into quarantine.
- DXV-side archiving and routing of picked-up files.
- Outbound PGP encryption implementation (only its file-selection contract).
- Provisioning of MinIO / Iceberg infrastructure.

## Test Environment

| Aspect | Setting |
| --- | --- |
| **Object store** | `MinIO (flow-wide bucket + credentials)` |
| **Table format** | `Apache Iceberg quarantine tables` |
| **Runner** | `pipeline.run_pipeline("failed-record-export", ...)` |
| **Key env vars** | `ORG_UNIT (optional), WORKSPACE_ID, CATALOG` |
| **Process date** | `process_date in YYYYMMDD` |

## User Story Index & Traceability

| Story Key | Functional Area / Title | Epic Theme | Test Cases | Priority | Document |
| --- | --- | --- | :---: | :---: | --- |
| `DXV-FRE-001` | Invoke the failed-record-export pipeline with correct parameter resolution | Pipeline Orchestration & Configuration | 7 | Highest | [`DXV-FRE-001_Pipeline-Invocation-and-Parameter-Resolution.md`](DXV-FRE-001_Pipeline-Invocation-and-Parameter-Resolution.md) |
| `DXV-FRE-002` | Read Iceberg quarantine tables and iterate contract tables safely | Quarantine Source Acquisition | 6 | Highest | [`DXV-FRE-002_Quarantine-Source-Reading-and-Iteration.md`](DXV-FRE-002_Quarantine-Source-Reading-and-Iteration.md) |
| `DXV-FRE-003` | Resolve, normalise and prefix output object paths correctly | Output Layout & Object Keys | 5 | High | [`DXV-FRE-003_Path-Resolution-Normalisation-and-ORG_UNIT.md`](DXV-FRE-003_Path-Resolution-Normalisation-and-ORG_UNIT.md) |
| `DXV-FRE-004` | Generate clean-bad, aggregated and detailed export files correctly | Data Export Content | 6 | Highest | [`DXV-FRE-004_Data-File-Generation-Bad-Aggregated-Detailed.md`](DXV-FRE-004_Data-File-Generation-Bad-Aggregated-Detailed.md) |
| `DXV-FRE-005` | Emit the correct acquisition success / error envelope flag per run | Feedback Flags & Envelope Semantics | 6 | Highest | [`DXV-FRE-005_Envelope-Flag-File-Generation-and-Semantics.md`](DXV-FRE-005_Envelope-Flag-File-Generation-and-Semantics.md) |
| `DXV-FRE-006` | Apply export file_format, separator and header rules correctly | Writer Format & Delimiters | 8 | High | [`DXV-FRE-006_Export-Format-Delimiter-and-Header-Handling.md`](DXV-FRE-006_Export-Format-Delimiter-and-Header-Handling.md) |
| `DXV-FRE-007` | Align headerless export shape with RFFilespec ingest | RFFilespec / Headerless Compatibility | 4 | Medium | [`DXV-FRE-007_RFFilespec-Headerless-Alignment.md`](DXV-FRE-007_RFFilespec-Headerless-Alignment.md) |
| `DXV-FRE-008` | Write .keep prefix markers and apply *.zip.flag naming conventions | Object-Store Behaviour & Naming | 6 | High | [`DXV-FRE-008_Storage-Behaviour-Keep-Markers-and-Zip-Flag-Naming.md`](DXV-FRE-008_Storage-Behaviour-Keep-Markers-and-Zip-Flag-Naming.md) |
| `DXV-FRE-009` | Integrate exports with DXV pickup and align resubmit keys with ingest | Downstream Integration & Round-Trip | 6 | High | [`DXV-FRE-009_Downstream-DXV-Integration-and-Ingest-Alignment.md`](DXV-FRE-009_Downstream-DXV-Integration-and-Ingest-Alignment.md) |
| `DXV-FRE-010` | Validate non-functional qualities of the quarantine export stage | Non-Functional Quality | 8 | High | [`DXV-FRE-010_Non-Functional-Requirements.md`](DXV-FRE-010_Non-Functional-Requirements.md) |

## How to Use This Suite

- Each User Story is delivered as a standalone Word (`.docx`) document and a parallel Markdown (`.md`) file with identical content. The Markdown files carry YAML front matter and are intended for automated import into Atlassian JIRA Cloud.
- Execute the test cases in the order presented within each story. *Happy Path* cases establish baseline behaviour; *Negative*, *Boundary*, *Security* and *Non-Functional* cases probe edges, failure handling and quality attributes.
- Substitute the example test-data values (`process_date`, table names, paths, thresholds) with values appropriate to your environment and SLAs before execution.

---

_Source: `feedback-quarantine-export.md` — generated 2026-06-11._
