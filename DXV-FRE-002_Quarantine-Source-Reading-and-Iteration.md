---
jira_issue_type: "Story"
story_key: "DXV-FRE-002"
summary: "Read Iceberg quarantine tables and iterate contract tables safely"
epic: "Quarantine Source Acquisition"
priority: "Highest"
story_points: 5
components: ["failed-record-export"]
labels: ["dxv", "failed-record-export", "iceberg", "quarantine", "integration"]
status: "Ready for Test"
test_case_count: 6
test_type_breakdown: {"Happy Path": 2, "Negative": 2, "Boundary": 2}
---

# DXV-FRE-002 — Read Iceberg quarantine tables and iterate contract tables safely

> **Epic:** Quarantine Source Acquisition  |  **Product:** DXV — Data Exchange Vault  |  **Pipeline:** `failed-record-export`

## Story Details

| Field | Value |
| --- | --- |
| **Story Key** | `DXV-FRE-002` |
| **Issue Type** | Story |
| **Epic** | Quarantine Source Acquisition |
| **Priority** | **Highest** |
| **Story Points** | 5 |
| **Components** | `failed-record-export` |
| **Labels** | `dxv` `failed-record-export` `iceberg` `quarantine` `integration` |
| **Status** | Ready for Test |

## User Story

> **As a** AML data engineer  
> **I want** the exporter to resolve and read the correct Iceberg quarantine table for each logical table in the contract for the run's process_date  
> **so that** every table that genuinely has validation failures is exported, while tables with no quarantine data are skipped without failing the whole run.

## Description

For each table_name listed in the contract's tables[] array, the exporter reads the corresponding Iceberg quarantine table. The quarantine table name is derived as {CATALOG}.{WORKSPACE_ID}.quarantine_{table_name}_{process_date}, where CATALOG and WORKSPACE_ID come from the environment.

These quarantine rows are exactly the rows that previously failed data-validation in the upstream stage. The exporter does not re-run validation; it reads what is already quarantined for that table and date.

Resilience is a core requirement: if a quarantine table for a given contract table does not exist for that date (for example there were no failed rows, or the quarantine table was already dropped), that table is skipped. A missing table is NOT a hard failure for the whole export — other tables continue to be processed.

## Key Terms & Behaviour

| Term | Behaviour / Definition |
| --- | --- |
| **Quarantine table name** | {CATALOG}.{WORKSPACE_ID}.quarantine_{table_name}_{process_date} |
| **Source rows** | Rows that already failed data-validation upstream. |
| **tables[]** | Logical table_name entries in the contract JSON whose quarantine tables are export sources. |
| **Missing table** | Skipped (not a hard failure) — e.g. no failed rows, or quarantine already dropped. |

## Acceptance Criteria

**Definition of Done**

1. For each table_name in tables[], the exporter targets {CATALOG}.{WORKSPACE_ID}.quarantine_{table_name}_{process_date}.
2. Tables whose quarantine table exists and has rows are exported.
3. A contract table whose quarantine table is absent for the date is skipped and the run continues.
4. A run where every contract table is missing completes without a hard failure and produces the acquisition-success outcome (no rows exported).
5. CATALOG and WORKSPACE_ID are sourced from the environment and used verbatim in the resolved table name.

## Recommended Test Data

| Artefact | Example Value / Format |
| --- | --- |
| **CATALOG** | `aml_catalog` |
| **WORKSPACE_ID** | `ws_001` |
| **table_name(s)** | `customer, account, transaction` |
| **process_date** | `20260313` |
| **Resolved name** | `aml_catalog.ws_001.quarantine_customer_20260313` |
| **Contract tables[]** | `["customer", "account", "transaction"]` |

## Global Preconditions

- CATALOG and WORKSPACE_ID environment variables are set for the deployment.
- The data contract lists the tables under test in tables[].

## Test Cases

**Coverage:** 6 test case(s) — 🟢 Happy Path × 2  🔴 Negative × 2  🟠 Boundary × 2

---

### 🟢 TC-001 — Happy path — single table with failures is read & exported

**Type:** Happy Path  |  **Priority:** Highest

**Objective:** A populated quarantine table is correctly resolved and exported.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Seed a quarantine table with failed rows. | `aml_catalog.ws_001.quarantine_customer_20260313 with 25 rows` | Table exists and is populated. |
| 2 | Set contract tables[] to a single table. | `tables[] = ["customer"]` | Contract valid. |
| 3 | Run the export for process_date 20260313. | `run_pipeline("failed-record-export", ..., process_date="20260313")` | Run completes; the customer quarantine table is read. |
| 4 | Verify exported objects for customer. | `Inspect bad/aggregated/detailed objects for customer_20260313` | All three data files are produced and contain the 25 rows / their aggregation. |

---

### 🟢 TC-002 — Happy path — multiple tables, mixed content

**Type:** Happy Path  |  **Priority:** High

**Objective:** Each contract table is resolved independently; populated ones export, the empty/missing one is skipped.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Seed two of three quarantine tables. | `customer (10 rows), transaction (4 rows); account quarantine table absent` | Two tables populated, one missing. |
| 2 | Set contract tables[] to all three. | `tables[] = ["customer", "account", "transaction"]` | Contract valid. |
| 3 | Run the export. | `process_date=20260313` | Run completes without error. |
| 4 | Verify outputs per table. | `List objects for each table` | customer and transaction have data files; account has none; the run did not fail because of account. |

---

### 🔴 TC-003 — Negative/Resilience — single missing quarantine table is skipped

**Type:** Negative  |  **Priority:** Highest

**Objective:** An absent quarantine table for one contract table must not fail the run.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Ensure the quarantine table for one contract table does not exist. | `Drop / never create aml_catalog.ws_001.quarantine_account_20260313` | Table is absent for the date. |
| 2 | Run the export with that table present in tables[]. | `tables[] includes "account"` | Run completes successfully (no hard failure). |
| 3 | Inspect logs / summary for the skipped table. | `Return dict / logs` | account is reported as skipped; other tables processed normally. |

---

### 🟠 TC-004 — Boundary — all contract tables missing

**Type:** Boundary  |  **Priority:** High

**Objective:** When no quarantine tables exist for any contract table, the run still succeeds with a no-rows outcome.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Ensure no quarantine tables exist for the date. | `No quarantine_* tables for 20260313` | All sources absent. |
| 2 | Run the export. | `tables[] = ["customer", "account", "transaction"]` | Run completes without a hard failure. |
| 3 | Verify the run is treated as acquisition-success. | `Inspect feedback flag (see DXV-FRE-005)` | No data exports for any table; an acq_success flag is the outcome (no quarantine rows exported). |

---

### 🟠 TC-005 — Boundary — quarantine table exists but is empty (0 rows)

**Type:** Boundary  |  **Priority:** Medium

**Objective:** An existing-but-empty quarantine table is handled deterministically.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Create an empty quarantine table. | `aml_catalog.ws_001.quarantine_customer_20260313 with 0 rows` | Table exists, no rows. |
| 2 | Run the export. | `tables[] = ["customer"]` | Run completes. |
| 3 | Inspect outputs and flag. | `Data files + envelope outcome` | Behaviour is deterministic and documented (no failed rows contributes nothing to envelope_error); no crash on empty source. |

---

### 🔴 TC-006 — Negative — environment workspace/catalog mis-set

**Type:** Negative  |  **Priority:** Medium

**Objective:** Incorrect CATALOG/WORKSPACE_ID resolves to non-existent tables and is handled as skips, not crashes.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Set a wrong WORKSPACE_ID. | `WORKSPACE_ID=ws_does_not_exist` | Resolved quarantine names point at non-existent tables. |
| 2 | Run the export. | `process_date=20260313` | Tables resolve as missing and are skipped; the run does not crash with an unhandled error. |

---

_Generated for the DXV Feedback (Quarantine Export) integration test suite — 2026-06-11._
