---
jira_issue_type: "Story"
story_key: "DXV-FRE-009"
summary: "Integrate exports with DXV pickup and align resubmit keys with ingest"
epic: "Downstream Integration & Round-Trip"
priority: "High"
story_points: 5
components: ["failed-record-export", "ingest-to-staging"]
labels: ["dxv", "failed-record-export", "ingestion", "integration", "round-trip"]
status: "Ready for Test"
test_case_count: 6
test_type_breakdown: {"Happy Path": 5, "Negative": 1}
---

# DXV-FRE-009 — Integrate exports with DXV pickup and align resubmit keys with ingest

> **Epic:** Downstream Integration & Round-Trip  |  **Product:** DXV — Data Exchange Vault  |  **Pipeline:** `failed-record-export`

## Story Details

| Field | Value |
| --- | --- |
| **Story Key** | `DXV-FRE-009` |
| **Issue Type** | Story |
| **Epic** | Downstream Integration & Round-Trip |
| **Priority** | **High** |
| **Story Points** | 5 |
| **Components** | `failed-record-export`, `ingest-to-staging` |
| **Labels** | `dxv` `failed-record-export` `ingestion` `integration` `round-trip` |
| **Status** | Ready for Test |

## User Story

> **As a** AML operations engineer  
> **I want** the exporter to write flags and data under the roots DXV watches and to produce clean-bad keys that ingest-to-staging can resubmit without renaming  
> **so that** the failure feedback loop is fully automated end-to-end and corrected records flow straight back into ingestion.

## Description

This stage shares flow-wide MinIO bucket and credentials with the other MinIO-driven stages (e.g. ingest and validation). DXV (or a similar pickup service) must watch or move the roots in use — for example landing/acquisition/feedback/ and landing/acquisition/bad/ with the defaults. Archiving of picked-up files happens downstream on the DXV side and is not part of this stage. The pipeline runner returns a Python dict summarising the stage.

For the resubmit loop, ingest-to-staging resolves each table's upload from the exact object key {table_name}_{process_date}.{input.extension} under the ingest prefix. The clean-bad export key therefore needs to line up with that expected ingest key. If filenames differ, the operator must rename objects or adjust process_date / the contract so the key matches.

This story validates the integration seams: credentials reuse, DXV watching the correct roots, the returned summary dict, and the clean-bad -> ingest key round-trip.

## Key Terms & Behaviour

| Term | Behaviour / Definition |
| --- | --- |
| **Shared MinIO** | Same flow-wide bucket and credentials as ingest and validation stages. |
| **DXV watch roots** | DXV watches/moves the roots in use (e.g. .../feedback/ and .../bad/). |
| **Archiving** | Downstream on the DXV side, not part of this stage. |
| **Return value** | run_pipeline returns a Python dict summary for the stage. |
| **Ingest key** | ingest-to-staging resolves {table_name}_{process_date}.{input.extension} under the ingest prefix. |
| **Mismatch remedy** | Rename objects or adjust process_date / contract so the key matches. |

## Acceptance Criteria

**Definition of Done**

1. The stage reads/writes using the same flow-wide MinIO bucket and credentials as other stages (no separate credential set required).
2. Flags and data land under the roots DXV is configured to watch (defaults: feedback/ and bad/).
3. run_pipeline returns a Python dict summary describing the run.
4. A clean-bad object named {table_name}_{process_date}.{ext} is resolvable by ingest-to-staging when the extension matches input.extension.
5. When export key and ingest-expected key differ, the documented remedy (rename / adjust process_date or contract) makes the round-trip succeed.

## Recommended Test Data

| Artefact | Example Value / Format |
| --- | --- |
| **Bucket/credentials** | `flow-wide MinIO settings (shared)` |
| **DXV-watched roots** | `landing/acquisition/feedback/, landing/acquisition/bad/` |
| **Clean-bad key** | `landing/acquisition/bad/20260313/customer_20260313.csv` |
| **Ingest-expected key** | `<ingest prefix>/customer_20260313.csv  (input.extension=csv)` |
| **Return value** | `Python dict (tables processed, objects written, flag emitted, ...)` |

## Global Preconditions

- Flow-wide MinIO bucket/credentials are configured and shared across stages.
- A DXV (or stub) pickup watcher is configured against the roots under test.
- ingest-to-staging is available to validate the resubmit key round-trip.

## Test Cases

**Coverage:** 6 test case(s) — 🟢 Happy Path × 5  🔴 Negative × 1

---

### 🟢 TC-001 — Happy path — shared MinIO credentials reused

**Type:** Happy Path  |  **Priority:** High

**Objective:** The stage uses the flow-wide bucket/credentials with no separate config.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Configure only the flow-wide MinIO settings (as used by ingest/validation). | `Shared bucket + credentials; no export-specific credential override` | Settings present. |
| 2 | Run the export. | `process_date=20260313; table=customer` | Run completes; objects written to the shared bucket without extra credentials. |

---

### 🟢 TC-002 — Happy path — DXV picks up flag + data from watched roots

**Type:** Happy Path  |  **Priority:** High

**Objective:** Objects land under the DXV-watched roots and are detected by the pickup watcher.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Configure DXV (or stub) to watch the feedback and bad roots. | `Watch landing/acquisition/feedback/ and landing/acquisition/bad/` | Watcher active. |
| 2 | Run an export with failures. | `customer populated; process_date=20260313` | Run completes; envelope_error flag + clean-bad written under watched roots. |
| 3 | Observe DXV pickup. | `Watcher events / moved objects` | DXV detects the flag and data objects under the watched roots. |

---

### 🟢 TC-003 — Happy path — clean-bad key resubmits via ingest-to-staging

**Type:** Happy Path  |  **Priority:** High

**Objective:** A clean-bad object is resolvable by ingest using the exact key pattern.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Run the export producing a clean-bad object. | `file_format=csv (input.extension=csv); table=customer; process_date=20260313` | customer_20260313.csv written. |
| 2 | Place/point the clean-bad object at the ingest prefix. | `Key {table_name}_{process_date}.{input.extension} under ingest prefix` | Key matches the ingest-expected pattern. |
| 3 | Run ingest-to-staging for the same table/date. | `ingest-to-staging, customer, 20260313` | Ingest resolves and loads the object without renaming. |

---

### 🔴 TC-004 — Negative — key mismatch blocks resubmit until remedied

**Type:** Negative  |  **Priority:** Medium

**Objective:** A mismatched key is not silently ingested; the documented remedy fixes it.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Create an export key that does not match ingest expectations. | `Export ext .pipe but input.extension=csv (key customer_20260313.pipe)` | Keys differ. |
| 2 | Run ingest-to-staging. | `ingest-to-staging, customer, 20260313` | Ingest does NOT resolve the mismatched key (no silent load). |
| 3 | Apply the documented remedy and re-run. | `Rename to customer_20260313.csv OR align contract/file_format` | After remedy, ingest resolves and loads the object. |

---

### 🟢 TC-005 — Happy path — return value summary is well-formed

**Type:** Happy Path  |  **Priority:** Medium

**Objective:** run_pipeline returns a usable dict summary for orchestration.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Run the export and capture the return value. | `result = run_pipeline("failed-record-export", ...)` | result is a Python dict. |
| 2 | Inspect the summary contents. | `result keys/values` | Dict conveys the run outcome (e.g. tables processed/skipped, objects written, flag type) usable by an orchestrator. |

---

### 🟢 TC-006 — Happy path — archiving is downstream (not this stage)

**Type:** Happy Path  |  **Priority:** Low

**Objective:** This stage does not archive picked-up files; that is DXV's responsibility.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Run the export and let DXV pick up the objects. | `process_date=20260313` | Objects written and picked up. |
| 2 | Verify this stage performs no archiving itself. | `Inspect stage actions/logs` | No archive step is performed by failed-record-export; archiving is observed only on the DXV side. |

---

_Generated for the DXV Feedback (Quarantine Export) integration test suite — 2026-06-11._
