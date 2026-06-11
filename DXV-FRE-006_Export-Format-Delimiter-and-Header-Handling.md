---
jira_issue_type: "Story"
story_key: "DXV-FRE-006"
summary: "Apply export file_format, separator and header rules correctly"
epic: "Writer Format & Delimiters"
priority: "High"
story_points: 5
components: ["failed-record-export"]
labels: ["dxv", "failed-record-export", "format", "delimiter", "header", "integration"]
status: "Ready for Test"
test_case_count: 8
test_type_breakdown: {"Happy Path": 6, "Negative": 1, "Boundary": 1}
---

# DXV-FRE-006 — Apply export file_format, separator and header rules correctly

> **Epic:** Writer Format & Delimiters  |  **Product:** DXV — Data Exchange Vault  |  **Pipeline:** `failed-record-export`

## Story Details

| Field | Value |
| --- | --- |
| **Story Key** | `DXV-FRE-006` |
| **Issue Type** | Story |
| **Epic** | Writer Format & Delimiters |
| **Priority** | **High** |
| **Story Points** | 5 |
| **Components** | `failed-record-export` |
| **Labels** | `dxv` `failed-record-export` `format` `delimiter` `header` `integration` |
| **Status** | Ready for Test |

## User Story

> **As a** downstream integration engineer  
> **I want** control over the export file extension, delimiter and header, including reusing the ingest settings or overriding them with export-only values  
> **so that** exported keys and content match what downstream pickup expects, even when export formatting must differ from the ingest formatting.

## Description

The three data exports share one writer contract: a delimiter (separator) and a header flag from the merged spec. The contract's input.extension and input.delimiter seed the export file_format and separator unless top-level overrides are set. Supported export extensions for object names are csv and txt; {ext} follows file_format.

Two export-only file_format values exist for when export keys must differ from ingest: pipe and gs. These fix the separator in the writer. For example, with ingest input={extension:csv, delimiter:'|'} and export file_format=pipe, keys use .pipe. To get .csv keys with pipe-separated content instead, set file_format=csv and separator='|'.

txt export defaults to a tab separator if none is set. include_header is a boolean that defaults to true. All of file_format, separator and include_header may be set at the top level of the contract JSON and/or via the matching run_pipeline kwargs.

## Key Terms & Behaviour

| Term | Behaviour / Definition |
| --- | --- |
| **Seeding** | input.extension / input.delimiter seed export file_format / separator unless overridden. |
| **Ingest extensions** | Ingest allows input.extension csv / txt only on MinIO object names. |
| **Export-only formats** | pipe and gs fix the separator in the writer; used when export keys differ from ingest. |
| **.csv with pipe content** | Use file_format=csv and separator='\|' (keys end .csv, content pipe-separated). |
| **txt default separator** | Tab, if no separator is set. |
| **include_header** | Boolean, default true. |

## Acceptance Criteria

**Definition of Done**

1. With no overrides, export file_format and separator are seeded from input.extension and input.delimiter.
2. A top-level file_format / separator / include_header overrides the seeded value.
3. file_format=pipe and file_format=gs fix the writer separator and produce .pipe / .gs object keys respectively.
4. file_format=csv with separator='|' produces .csv keys whose content is pipe-separated.
5. txt export with no separator uses a tab delimiter.
6. include_header=true emits a header row; include_header=false omits it.

## Recommended Test Data

| Artefact | Example Value / Format |
| --- | --- |
| **input.extension / delimiter** | `csv / ',' (seeds export csv + comma)` |
| **file_format=txt** | `no separator -> tab-delimited, .txt keys` |
| **file_format=pipe** | `keys end .pipe; separator fixed by writer` |
| **file_format=gs** | `keys end .gs; separator fixed by writer` |
| **csv + separator '\|'** | `.csv keys, pipe-separated content` |
| **include_header** | `true (default) \| false` |

## Global Preconditions

- A populated quarantine table exists for the table/date under test.
- Contract input.extension/input.delimiter are set to known seed values.

## Test Cases

**Coverage:** 8 test case(s) — 🟢 Happy Path × 6  🔴 Negative × 1  🟠 Boundary × 1

---

### 🟢 TC-001 — Happy path — seed from ingest (csv, comma)

**Type:** Happy Path  |  **Priority:** High

**Objective:** With no overrides, export inherits csv extension and comma separator from ingest.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Set contract ingest settings; no export overrides. | `input={extension:'csv', delimiter:','}` | Contract valid. |
| 2 | Run the export. | `process_date=20260313; table=customer` | Run completes. |
| 3 | Inspect object key extension and content delimiter. | `customer_20260313.csv` | Key ends .csv; rows are comma-separated; header present by default. |

---

### 🟢 TC-002 — Happy path — txt defaults to tab

**Type:** Happy Path  |  **Priority:** High

**Objective:** file_format=txt with no separator yields tab-delimited content.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Set file_format=txt with no separator. | `file_format='txt'  (separator unset)` | Config accepted. |
| 2 | Run the export. | `process_date=20260313; table=customer` | Run completes. |
| 3 | Inspect key and delimiter. | `customer_20260313.txt` | Key ends .txt; fields are separated by a TAB character. |

---

### 🟢 TC-003 — Happy path — export-only pipe format (.pipe keys)

**Type:** Happy Path  |  **Priority:** High

**Objective:** file_format=pipe fixes the separator and emits .pipe object keys.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Configure ingest csv but export pipe. | `input={extension:'csv', delimiter:'\|'}; file_format='pipe'` | Config accepted. |
| 2 | Run the export. | `process_date=20260313; table=customer` | Run completes. |
| 3 | Inspect key extension and content separator. | `customer_20260313.pipe` | Key ends .pipe; content separator is fixed by the writer for pipe. |

---

### 🟢 TC-004 — Happy path — csv keys with pipe content

**Type:** Happy Path  |  **Priority:** Medium

**Objective:** file_format=csv + separator='|' yields .csv keys whose content is pipe-separated.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Set file_format=csv and separator='\|'. | `file_format='csv'; separator='\|'` | Config accepted. |
| 2 | Run the export. | `process_date=20260313; table=customer` | Run completes. |
| 3 | Inspect key and content. | `customer_20260313.csv` | Key ends .csv but fields are separated by '\|'. |

---

### 🟢 TC-005 — Happy path — gs export-only format (.gs keys)

**Type:** Happy Path  |  **Priority:** Low

**Objective:** file_format=gs fixes the writer separator and emits .gs keys.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Set file_format=gs. | `file_format='gs'` | Config accepted. |
| 2 | Run the export and inspect. | `process_date=20260313; table=customer` | Key ends .gs; writer separator is fixed for gs. |

---

### 🟢 TC-006 — Happy path — include_header toggles header row

**Type:** Happy Path  |  **Priority:** High

**Objective:** Header row appears when true (default) and is omitted when false.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Run with include_header=true (default). | `include_header unset OR true` | Output has a header row as the first line. |
| 2 | Run with include_header=false. | `include_header=false` | Output has NO header row; first line is data. |

---

### 🔴 TC-007 — Negative — unsupported file_format value

**Type:** Negative  |  **Priority:** Medium

**Objective:** An unsupported file_format is rejected rather than silently producing an odd key.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Set an unsupported export format. | `file_format='parquet'` | Config is rejected with a clear error (supported: csv, txt, pipe, gs). |
| 2 | Confirm no malformed objects are written. | `List objects for 20260313` | No object with an unexpected extension is created. |

---

### 🟠 TC-008 — Boundary — delimiter collides with data content

**Type:** Boundary  |  **Priority:** Medium

**Objective:** When the chosen delimiter appears inside field values, content remains parseable.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Seed values containing the delimiter. | `Comma-delimited export; a name field value = 'Smith, John'` | Quarantine populated with delimiter-bearing values. |
| 2 | Run the export. | `file_format=csv; separator=','; table=customer` | Run completes. |
| 3 | Parse the output with the configured delimiter. | `Re-parse file` | Field 'Smith, John' stays a single field (proper quoting/escaping); column count per row is stable. |

---

_Generated for the DXV Feedback (Quarantine Export) integration test suite — 2026-06-11._
