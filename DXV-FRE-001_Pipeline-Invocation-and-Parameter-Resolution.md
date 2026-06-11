---
jira_issue_type: "Story"
story_key: "DXV-FRE-001"
summary: "Invoke the failed-record-export pipeline with correct parameter resolution"
epic: "Pipeline Orchestration & Configuration"
priority: "Highest"
story_points: 5
components: ["failed-record-export"]
labels: ["dxv", "failed-record-export", "pipeline", "configuration", "integration"]
status: "Ready for Test"
test_case_count: 7
test_type_breakdown: {"Happy Path": 3, "Negative": 3, "Boundary": 1}
---

# DXV-FRE-001 — Invoke the failed-record-export pipeline with correct parameter resolution

> **Epic:** Pipeline Orchestration & Configuration  |  **Product:** DXV — Data Exchange Vault  |  **Pipeline:** `failed-record-export`

## Story Details

| Field | Value |
| --- | --- |
| **Story Key** | `DXV-FRE-001` |
| **Issue Type** | Story |
| **Epic** | Pipeline Orchestration & Configuration |
| **Priority** | **Highest** |
| **Story Points** | 5 |
| **Components** | `failed-record-export` |
| **Labels** | `dxv` `failed-record-export` `pipeline` `configuration` `integration` |
| **Status** | Ready for Test |

## User Story

> **As a** AML data engineer  
> **I want** to trigger the failed-record-export stage through run_pipeline using a data contract path and a process_date, with optional keyword overrides  
> **so that** the quarantine export runs deterministically for the correct AML execution date and honours the documented configuration precedence.

## Description

The failed-record-export stage is invoked exactly like the other AML stages, via the shared run_pipeline runner. The caller supplies the bucket-relative path to the data contract JSON (minio_config_path) and the run's process_date in YYYYMMDD. All other behaviour — export path roots, delimiter and header handling — is resolved from a merged configuration.

Configuration is resolved with a strict precedence: run_pipeline keyword arguments take priority, then optional fields in the spec (contract) JSON, then the built-in defaults. The optional kwargs share the same names as the optional spec fields: bad_records_location, feedback_location, report_location, file_format, separator and include_header.

On completion the runner returns a Python dict summarising the stage. The minio_config_path used here must be a distinct name from json-transformation's config_path / CONFIG_PATH (which is the table-to-JSON config), and process_date is supplied only through run_pipeline(..., process_date=...) — it is then merged into the parsed spec.

## Key Terms & Behaviour

| Term | Behaviour / Definition |
| --- | --- |
| **minio_config_path** | Bucket-relative path to the data contract JSON; required. |
| **process_date** | Run date in YYYYMMDD; required on every run, supplied only via run_pipeline. |
| **Precedence** | kwargs -> optional fields in spec JSON -> built-in defaults. |
| **Optional kwargs** | bad_records_location, feedback_location, report_location, file_format, separator, include_header. |
| **Return value** | Python dict summary returned by the pipeline runner for this stage. |

## Acceptance Criteria

**Definition of Done**

1. GIVEN a valid contract path and process_date, WHEN run_pipeline("failed-record-export", ...) is called, THEN the stage executes and returns a summary dict.
2. A kwarg value overrides the same optional field in the spec JSON, which in turn overrides the built-in default.
3. process_date supplied via run_pipeline is merged into the parsed spec and used for all quarantine table names and output paths.
4. Omitting a required parameter (minio_config_path or process_date) fails fast with a clear error and writes no output objects.
5. The pipeline name string must be exactly "failed-record-export"; an unknown name is rejected.

## Recommended Test Data

| Artefact | Example Value / Format |
| --- | --- |
| **minio_config_path** | `config/aml/customer_contract.json` |
| **process_date (valid)** | `20260313` |
| **process_date (invalid)** | `2026-03-13, 13032026, 20261332, '', null` |
| **file_format kwarg** | `csv \| txt \| pipe \| gs` |
| **separator kwarg** | `',' \| '\|' \| '\t'` |
| **include_header kwarg** | `True \| False` |
| **Pipeline name** | `failed-record-export` |

## Global Preconditions

- MinIO bucket and credentials are configured flow-wide and reachable.
- A valid data contract JSON exists at the bucket-relative path under test.
- Quarantine Iceberg tables exist for at least one contract table for the chosen process_date (unless a test states otherwise).

## Test Cases

**Coverage:** 7 test case(s) — 🟢 Happy Path × 3  🔴 Negative × 3  🟠 Boundary × 1

---

### 🟢 TC-001 — Happy path — minimal valid invocation

**Type:** Happy Path  |  **Priority:** Highest

**Objective:** Confirm the stage runs with only the two required parameters and returns a summary dict.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Set environment variables for the run. | `minio_config_path=config/aml/customer_contract.json; process_date=20260313` | Variables are accepted; no error raised. |
| 2 | Call run_pipeline with the pipeline name and the two required params. | `run_pipeline("failed-record-export", minio_config_path=..., process_date="20260313")` | Stage starts and reads the contract JSON successfully. |
| 3 | Wait for the run to complete and capture the return value. | `result = <return of run_pipeline>` | run_pipeline returns a Python dict (not None / not an exception). |
| 4 | Inspect the returned summary dict. | `result keys/values` | Dict summarises the stage execution (e.g. tables processed, objects written, flag emitted). |

**Postconditions:**
- Output objects are written under the default roots for process_date 20260313.

---

### 🟢 TC-002 — Happy path — kwargs override spec fields

**Type:** Happy Path  |  **Priority:** High

**Objective:** Verify run_pipeline kwargs take precedence over the equivalent optional fields in the spec JSON.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Prepare a contract JSON that sets optional fields to known values. | `spec: file_format="csv", separator=",", include_header=true` | Contract is valid and parseable. |
| 2 | Invoke run_pipeline overriding the same fields via kwargs. | `file_format="pipe", separator="\|", include_header=False, process_date="20260313"` | Run completes successfully. |
| 3 | Examine the written object keys and file contents. | `Inspect exported data files for process_date` | Keys/content reflect kwargs (pipe format, '\|' separator, no header) — NOT the spec values. |

---

### 🟢 TC-003 — Happy path — spec fields override built-in defaults

**Type:** Happy Path  |  **Priority:** Medium

**Objective:** Verify optional spec fields are applied when no kwarg is supplied, overriding defaults.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Prepare a contract JSON overriding a default root. | `spec: bad_records_location="landing/acquisition/custom_bad"` | Contract is valid. |
| 2 | Invoke run_pipeline WITHOUT a bad_records_location kwarg. | `run_pipeline("failed-record-export", minio_config_path=..., process_date="20260313")` | Run completes. |
| 3 | Inspect where clean-bad rows were written. | `List objects under landing/acquisition/custom_bad/20260313/` | Clean-bad files are written under the spec-provided root, not the default landing/acquisition/bad. |

---

### 🔴 TC-004 — Negative — missing process_date

**Type:** Negative  |  **Priority:** Highest

**Objective:** The run must fail fast and write nothing when process_date is absent.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Invoke run_pipeline without process_date. | `run_pipeline("failed-record-export", minio_config_path=...)  # no process_date` | A clear, actionable error is raised indicating process_date is required. |
| 2 | Inspect MinIO for any new objects under the run prefixes. | `List bucket prefixes` | No data files, flags or .keep markers are created. |

---

### 🔴 TC-005 — Negative — missing / unresolvable contract path

**Type:** Negative  |  **Priority:** High

**Objective:** An invalid minio_config_path is rejected with a clear error.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Invoke run_pipeline with a non-existent contract path. | `minio_config_path=config/aml/does_not_exist.json; process_date=20260313` | Run fails with an error identifying the missing/unreadable contract object. |
| 2 | Verify no partial output is produced. | `List bucket prefixes for 20260313` | No objects written. |

---

### 🔴 TC-006 — Negative — unknown pipeline name

**Type:** Negative  |  **Priority:** Medium

**Objective:** Only the exact registered name is accepted.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Invoke run_pipeline with a misspelt name. | `run_pipeline("failed_record_export", ...)  # underscores, wrong` | Runner rejects the unknown pipeline name with a clear error; stage does not execute. |

---

### 🟠 TC-007 — Boundary — process_date format validation

**Type:** Boundary  |  **Priority:** High

**Objective:** Only well-formed YYYYMMDD dates are accepted; malformed values are rejected.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Run with a hyphenated date. | `process_date=2026-03-13` | Rejected as malformed (expected compact YYYYMMDD) OR no tables resolve — documented, deterministic failure, no partial writes. |
| 2 | Run with a DDMMYYYY value. | `process_date=13032026` | Does not silently succeed against 13-Mar tables; behaves deterministically per the YYYYMMDD contract. |
| 3 | Run with an impossible calendar date. | `process_date=20261332  (month 13, day 32)` | Rejected / yields no matching quarantine tables; no spurious output. |
| 4 | Run with empty and null values. | `process_date='' and process_date=None` | Rejected fast with a clear error; nothing written. |

---

_Generated for the DXV Feedback (Quarantine Export) integration test suite — 2026-06-11._
