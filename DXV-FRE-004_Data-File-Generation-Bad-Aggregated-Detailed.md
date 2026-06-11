---
jira_issue_type: "Story"
story_key: "DXV-FRE-004"
summary: "Generate clean-bad, aggregated and detailed export files correctly"
epic: "Data Export Content"
priority: "Highest"
story_points: 8
components: ["failed-record-export"]
labels: ["dxv", "failed-record-export", "exports", "aggregation", "integration"]
status: "Ready for Test"
test_case_count: 6
test_type_breakdown: {"Happy Path": 3, "Boundary": 2, "Negative": 1}
---

# DXV-FRE-004 — Generate clean-bad, aggregated and detailed export files correctly

> **Epic:** Data Export Content  |  **Product:** DXV — Data Exchange Vault  |  **Pipeline:** `failed-record-export`

## Story Details

| Field | Value |
| --- | --- |
| **Story Key** | `DXV-FRE-004` |
| **Issue Type** | Story |
| **Epic** | Data Export Content |
| **Priority** | **Highest** |
| **Story Points** | 8 |
| **Components** | `failed-record-export` |
| **Labels** | `dxv` `failed-record-export` `exports` `aggregation` `integration` |
| **Status** | Ready for Test |

## User Story

> **As a** AML data analyst  
> **I want** the exporter to produce three distinct files per table — a clean resubmit copy, an aggregated error summary, and a full detailed export  
> **so that** I can resubmit corrected records, triage error patterns quickly, and still retain the full per-row validation detail for investigation.

## Description

For each exported table the stage writes three data files using one shared writer contract (delimiter + header from the spec). The Clean bad file contains the same rows as quarantine but with the validation_errors and validation_timestamp columns dropped, so the file is a clean copy suitable for resubmission.

The Aggregated file contains counts per (error_type, field_name) after exploding the validation_errors array. Importantly, if every row has an empty or null errors array, the exporter writes one fallback summary row — (validation_error, empty field, total row count) — so the file is never header-only. This fallback aligns with the envelope flag behaviour when errors cannot be exploded.

The Detailed file is the full row set with validation_errors retained as JSON on each row. Object names follow the documented patterns: {table}_{date}, aggregated_{table}_{date} and detailed_{table}_{date}, each with the configured extension.

## Key Terms & Behaviour

| Term | Behaviour / Definition |
| --- | --- |
| **Clean bad** | Quarantine rows with validation_errors and validation_timestamp dropped. |
| **Aggregated** | Counts per (error_type, field_name) after exploding validation_errors. |
| **Aggregated fallback** | If all errors arrays empty/null -> one row: validation_error, empty field, total row count. |
| **Detailed** | Full row set with validation_errors as JSON on each row. |
| **Writer contract** | Delimiter + header come from the merged spec (see DXV-FRE-006). |

## Acceptance Criteria

**Definition of Done**

1. Clean-bad output contains all quarantine rows but excludes the validation_errors and validation_timestamp columns.
2. Aggregated output contains one row per distinct (error_type, field_name) with a correct count, derived by exploding validation_errors.
3. When all rows have empty/null validation_errors, the aggregated file contains exactly one fallback row: (validation_error, empty field, total row count) — never header-only.
4. Detailed output contains every quarantine row with validation_errors preserved as JSON.
5. All three files are written at the documented object keys with the configured extension and delimiter/header.

## Recommended Test Data

| Artefact | Example Value / Format |
| --- | --- |
| **Quarantine row** | `customer_id, name, ..., validation_errors (array), validation_timestamp` |
| **validation_errors element** | `{"error_type":"null_check","field_name":"customer_id"}` |
| **Multi-error row** | `[{null_check, customer_id}, {format, dob}]` |
| **Empty errors row** | `validation_errors = [] or null` |
| **Aggregated row** | `error_type, field_name, count  ->  null_check, customer_id, 12` |
| **Fallback aggregated row** | `validation_error, <empty>, <total row count>` |

## Global Preconditions

- A quarantine table for the table/date under test exists and is populated as the case requires.
- Spec delimiter/header are known so output content can be parsed and asserted.

## Test Cases

**Coverage:** 6 test case(s) — 🟢 Happy Path × 3  🟠 Boundary × 2  🔴 Negative × 1

---

### 🟢 TC-001 — Happy path — clean-bad drops validation columns

**Type:** Happy Path  |  **Priority:** Highest

**Objective:** Clean-bad file is a faithful copy minus validation_errors and validation_timestamp.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Seed quarantine rows including validation columns. | `10 rows, each with business columns + validation_errors + validation_timestamp` | Table populated. |
| 2 | Run the export. | `table=customer; process_date=20260313; file_format=csv; include_header=true` | Run completes; clean-bad object written. |
| 3 | Open the clean-bad file and inspect the header. | `landing/acquisition/bad/20260313/customer_20260313.csv` | Header contains business columns only; validation_errors and validation_timestamp are absent. |
| 4 | Count and spot-check rows. | `Compare to source` | Row count equals source (10); business values are unchanged. |

---

### 🟢 TC-002 — Happy path — aggregated counts per (error_type, field_name)

**Type:** Happy Path  |  **Priority:** Highest

**Objective:** Aggregation explodes validation_errors and counts each (error_type, field_name) pair.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Seed rows with known, countable errors. | `12 rows null_check/customer_id; 5 rows format/dob; 3 rows range/score` | Quarantine populated with a known error distribution. |
| 2 | Run the export. | `table=customer; process_date=20260313` | Aggregated object written. |
| 3 | Open the aggregated file and verify the rows. | `.../reporting/20260313/aggregated_customer_20260313.csv` | Rows: (null_check, customer_id, 12), (format, dob, 5), (range, score, 3); counts exactly match. |

---

### 🟠 TC-003 — Boundary — multi-error rows explode correctly

**Type:** Boundary  |  **Priority:** High

**Objective:** A single row carrying multiple errors increments each relevant (error_type, field_name).

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Seed rows where one row has two errors. | `Row A: [{null_check,customer_id},{format,dob}]; 4 more rows: [{null_check,customer_id}]` | Quarantine populated. |
| 2 | Run the export. | `table=customer; process_date=20260313` | Aggregated object written. |
| 3 | Verify the counts reflect exploded errors. | `Inspect aggregated rows` | (null_check, customer_id) = 5 and (format, dob) = 1 — the multi-error row contributes to both. |

---

### 🟠 TC-004 — Boundary — all-empty errors triggers single fallback row

**Type:** Boundary  |  **Priority:** Highest

**Objective:** When validation_errors cannot be exploded, the aggregated file holds exactly one fallback summary row.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Seed rows all with empty/null errors. | `8 rows, every validation_errors = [] or null` | Quarantine populated; nothing to explode. |
| 2 | Run the export. | `table=customer; process_date=20260313` | Aggregated object written. |
| 3 | Open the aggregated file. | `Inspect rows` | Exactly ONE data row: (validation_error, <empty field>, 8) — the total row count; file is NOT header-only. |
| 4 | Cross-check the envelope flag outcome. | `See DXV-FRE-005` | Fallback aligns with envelope_error single fallback line for that table. |

---

### 🟢 TC-005 — Happy path — detailed retains validation_errors as JSON

**Type:** Happy Path  |  **Priority:** High

**Objective:** Detailed file keeps the full row set with validation_errors serialised as JSON.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Seed rows with structured errors. | `6 rows with non-empty validation_errors arrays` | Quarantine populated. |
| 2 | Run the export. | `table=customer; process_date=20260313` | Detailed object written. |
| 3 | Open the detailed file and inspect a row's validation_errors cell. | `.../reporting/20260313/detailed_customer_20260313.csv` | Cell contains valid JSON (e.g. [{"error_type":"null_check","field_name":"customer_id"}]); all 6 rows present. |
| 4 | Confirm delimiter does not corrupt embedded JSON. | `Parse the file with the configured delimiter` | JSON commas do not break columns (proper quoting/escaping applied). |

---

### 🔴 TC-006 — Negative — malformed validation_errors payload

**Type:** Negative  |  **Priority:** Medium

**Objective:** A row with a malformed errors payload is handled without aborting the whole export.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Seed a row with a non-array / malformed errors value. | `validation_errors = '{not-json' on one row, valid on others` | Quarantine populated with one bad payload. |
| 2 | Run the export. | `table=customer; process_date=20260313` | Run completes; the export does not crash on the single malformed payload. |
| 3 | Inspect aggregated/detailed handling of the bad row. | `Review outputs / logs` | Bad payload is handled deterministically (e.g. counted under fallback / surfaced), other rows unaffected. |

---

_Generated for the DXV Feedback (Quarantine Export) integration test suite — 2026-06-11._
