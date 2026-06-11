---
jira_issue_type: "Story"
story_key: "DXV-FRE-007"
summary: "Align headerless export shape with RFFilespec ingest"
epic: "RFFilespec / Headerless Compatibility"
priority: "Medium"
story_points: 3
components: ["failed-record-export"]
labels: ["dxv", "failed-record-export", "rffilespec", "headerless", "integration"]
status: "Ready for Test"
test_case_count: 4
test_type_breakdown: {"Negative": 1, "Happy Path": 3}
---

# DXV-FRE-007 — Align headerless export shape with RFFilespec ingest

> **Epic:** RFFilespec / Headerless Compatibility  |  **Product:** DXV — Data Exchange Vault  |  **Pipeline:** `failed-record-export`

## Story Details

| Field | Value |
| --- | --- |
| **Story Key** | `DXV-FRE-007` |
| **Issue Type** | Story |
| **Epic** | RFFilespec / Headerless Compatibility |
| **Priority** | **Medium** |
| **Story Points** | 3 |
| **Components** | `failed-record-export` |
| **Labels** | `dxv` `failed-record-export` `rffilespec` `headerless` `integration` |
| **Status** | Ready for Test |

## User Story

> **As a** AML data engineer  
> **I want** headerless bad-row and report files when ingest uses RFFilespec/XML-driven, headerless column ordering  
> **so that** the resubmit and report files match the exact shape the ingest expects, avoiding a header line that RFFilespec ingest would not tolerate.

## Description

When the contract sets input.use_rffilespec to true, ingest uses headerless, RFFilespec/XML-driven column ordering. Failed-record export, however, still defaults include_header to true regardless of use_rffilespec.

Therefore, to produce headerless bad rows and reports that match the RFFilespec ingest shape, the team must explicitly set include_header to false — either in the contract JSON or by passing include_header=False to run_pipeline.

Export path roots remain global for this stage (bad_records_location, feedback_location, report_location). There is no separate per-table export path layout introduced by RFFilespec; only the header behaviour needs aligning.

## Key Terms & Behaviour

| Term | Behaviour / Definition |
| --- | --- |
| **input.use_rffilespec** | When true, ingest is headerless with XML-driven column order. |
| **Export default** | include_header still defaults to true even when use_rffilespec is true. |
| **Required action** | Set include_header=false (contract) or include_header=False (kwarg) for headerless export. |
| **Path roots** | Remain global (bad/feedback/report); no per-table export path layout. |

## Acceptance Criteria

**Definition of Done**

1. With use_rffilespec=true and no header override, export still emits a header row (documented default).
2. With use_rffilespec=true and include_header=false (contract or kwarg), bad rows and reports are headerless.
3. Headerless output column order is consistent with the RFFilespec/XML-driven ingest order.
4. Export path roots remain the global bad/feedback/report roots regardless of use_rffilespec.

## Recommended Test Data

| Artefact | Example Value / Format |
| --- | --- |
| **input.use_rffilespec** | `true` |
| **include_header (kwarg)** | `False` |
| **include_header (contract)** | `false` |
| **table_name** | `customer` |
| **process_date** | `20260313` |

## Global Preconditions

- A contract configured with input.use_rffilespec=true and a corresponding RFFilespec/XML column order.
- A populated quarantine table for the table/date under test.

## Test Cases

**Coverage:** 4 test case(s) — 🔴 Negative × 1  🟢 Happy Path × 3

---

### 🔴 TC-001 — Negative/Default — rffilespec true but header not overridden

**Type:** Negative  |  **Priority:** High

**Objective:** Confirm export still emits a header by default even with use_rffilespec=true (documents the gotcha).

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Configure contract with use_rffilespec=true and no header override. | `input.use_rffilespec=true; include_header unset` | Contract valid. |
| 2 | Run the export. | `process_date=20260313; table=customer` | Run completes. |
| 3 | Inspect the clean-bad file's first line. | `Open customer_20260313 export` | A header row IS present (export default true) — i.e. it does NOT auto-match headerless ingest. |

---

### 🟢 TC-002 — Happy path — headerless via kwarg

**Type:** Happy Path  |  **Priority:** High

**Objective:** include_header=False kwarg produces headerless bad rows and reports.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Run with use_rffilespec=true and include_header=False kwarg. | `run_pipeline(..., include_header=False, process_date="20260313")` | Run completes. |
| 2 | Inspect bad, aggregated and detailed files. | `Open all three exports for customer` | None of the files contain a header row; the first line is data. |
| 3 | Verify column order matches RFFilespec/XML order. | `Compare to the ingest column order` | Headerless columns are positioned to match the RFFilespec-driven ingest shape. |

---

### 🟢 TC-003 — Happy path — headerless via contract field

**Type:** Happy Path  |  **Priority:** Medium

**Objective:** include_header=false in the contract JSON also yields headerless output.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Set include_header=false in the contract; no kwarg. | `contract: include_header=false; use_rffilespec=true` | Contract valid. |
| 2 | Run the export. | `process_date=20260313; table=customer` | Run completes. |
| 3 | Inspect output header behaviour. | `Open exports` | Files are headerless, matching the contract setting. |

---

### 🟢 TC-004 — Happy path — global roots unaffected by rffilespec

**Type:** Happy Path  |  **Priority:** Low

**Objective:** Export path roots remain the global bad/feedback/report roots under RFFilespec.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Run a headerless RFFilespec export. | `use_rffilespec=true; include_header=False; process_date=20260313` | Run completes. |
| 2 | Inspect object keys. | `List keys for the date` | Objects are under the same global bad/feedback/report roots; no per-table export path layout appears. |

---

_Generated for the DXV Feedback (Quarantine Export) integration test suite — 2026-06-11._
