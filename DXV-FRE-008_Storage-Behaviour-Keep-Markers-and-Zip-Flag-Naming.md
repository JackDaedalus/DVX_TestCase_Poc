---
jira_issue_type: "Story"
story_key: "DXV-FRE-008"
summary: "Write .keep prefix markers and apply *.zip.flag naming conventions"
epic: "Object-Store Behaviour & Naming"
priority: "High"
story_points: 5
components: ["failed-record-export"]
labels: ["dxv", "failed-record-export", "minio", "keep-markers", "naming", "integration"]
status: "Ready for Test"
test_case_count: 6
test_type_breakdown: {"Happy Path": 3, "Boundary": 1, "Security": 1, "Negative": 1}
---

# DXV-FRE-008 — Write .keep prefix markers and apply *.zip.flag naming conventions

> **Epic:** Object-Store Behaviour & Naming  |  **Product:** DXV — Data Exchange Vault  |  **Pipeline:** `failed-record-export`

## Story Details

| Field | Value |
| --- | --- |
| **Story Key** | `DXV-FRE-008` |
| **Issue Type** | Story |
| **Epic** | Object-Store Behaviour & Naming |
| **Priority** | **High** |
| **Story Points** | 5 |
| **Components** | `failed-record-export` |
| **Labels** | `dxv` `failed-record-export` `minio` `keep-markers` `naming` `integration` |
| **Status** | Ready for Test |

## User Story

> **As a** platform integration engineer  
> **I want** every run to create the three date-prefix .keep markers and to name flag objects with the DXV-compatible *.zip.flag convention  
> **so that** downstream object-store tooling always finds a concrete prefix key to watch, and outbound PGP/zip routing treats the flags correctly as non-zip objects.

## Description

Before any per-table exports, every run writes three zero-byte .keep objects — one under {bad_records_location}/{process_date}/, one under {report_location}/{process_date}/ and one under {feedback_location}/{process_date}/ (after any ORG_UNIT prefix). These markers are unconditional: they are written whether or not there are quarantine rows, ensuring each date prefix exists as a concrete object-store key for downstream tooling. The bad, aggregated, detailed and flag objects are each written as one object per filename at the documented paths.

Flag objects are named *.zip.flag. The .zip in the filename is a DXV convention that is backwards compatible with NetReveal naming (flags historically paired by basename with envelope_*.zip flows). This stage does NOT write a .zip archive next to those flags — bad rows and reports are delimiter-separated files and flag bodies are plain text. The .zip segment exists only in the object name for integration compatibility.

This matters for outbound PGP: handlers that encrypt outbound files often key off paths ending with .zip. Because acq_success_* and envelope_error_* objects are named *.zip.flag, the path ends with .flag (not .zip), so they are NOT treated as zip payloads by that branch and are handled like other non-.zip objects.

## Key Terms & Behaviour

| Term | Behaviour / Definition |
| --- | --- |
| **.keep markers** | Three zero-byte objects per run under bad/report/feedback date prefixes. |
| **Unconditional** | Written before per-table exports, regardless of quarantine rows. |
| **Single keys** | bad, aggregated, detailed and flag objects: one object per filename. |
| **.zip.flag convention** | DXV/NetReveal-compatible naming; no companion .zip archive is written. |
| **PGP routing** | Path ends with .flag not .zip, so flags are handled as non-zip objects. |

## Acceptance Criteria

**Definition of Done**

1. Every run writes exactly three .keep objects, one under each of the bad/report/feedback date prefixes (after any ORG_UNIT prefix).
2. .keep markers are created even when there are zero quarantine rows.
3. .keep markers are zero-byte and exist before/independent of per-table exports.
4. Flag object names end with .zip.flag and no companion .zip archive is written alongside.
5. Each of bad/aggregated/detailed/flag is written as a single object per filename at the documented path.
6. Because the key ends with .flag (not .zip), the flag is treated as a non-zip object by outbound routing.

## Recommended Test Data

| Artefact | Example Value / Format |
| --- | --- |
| **process_date** | `20260313` |
| **bad .keep key** | `landing/acquisition/bad/20260313/.keep` |
| **report .keep key** | `landing/acquisition/feedback/reporting/20260313/.keep` |
| **feedback .keep key** | `landing/acquisition/feedback/20260313/.keep` |
| **flag name** | `envelope_error_20260313.zip.flag / acq_success_20260313.zip.flag` |
| **companion zip** | `NONE expected (no *.zip object next to the flag)` |

## Global Preconditions

- A clean MinIO prefix for the date (so created objects can be counted unambiguously).
- ORG_UNIT set or unset per the individual test.

## Test Cases

**Coverage:** 6 test case(s) — 🟢 Happy Path × 3  🟠 Boundary × 1  🟣 Security × 1  🔴 Negative × 1

---

### 🟢 TC-001 — Happy path — three .keep markers created (with rows)

**Type:** Happy Path  |  **Priority:** High

**Objective:** A normal run writes the three date-prefix .keep markers.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Run an export that has quarantine rows. | `customer populated; process_date=20260313` | Run completes. |
| 2 | List objects under each date prefix. | `bad/20260313/, feedback/reporting/20260313/, feedback/20260313/` | Each prefix contains a .keep object (3 total). |
| 3 | Verify each .keep object size. | `Inspect content-length` | Each .keep is zero bytes. |

---

### 🟠 TC-002 — Boundary — .keep markers created with NO rows

**Type:** Boundary  |  **Priority:** High

**Objective:** The markers are unconditional, even when nothing is exported.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Run an export with no quarantine rows for any table. | `All sources empty/missing; process_date=20260313` | Run completes (acq_success outcome). |
| 2 | List the three date prefixes. | `bad/report/feedback for 20260313` | All three .keep markers still exist despite zero exported data files. |

---

### 🟢 TC-003 — Happy path — .keep markers respect ORG_UNIT prefix

**Type:** Happy Path  |  **Priority:** Medium

**Objective:** When ORG_UNIT is set, the .keep markers are created under the prefixed paths.

**Preconditions:**
- ORG_UNIT=OrgA

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Run with ORG_UNIT set. | `ORG_UNIT=OrgA; process_date=20260313` | Run completes. |
| 2 | Locate the .keep markers. | `<orgunit-prefix>/.../20260313/.keep` | All three markers exist beneath the ORG_UNIT-prefixed roots. |

---

### 🟢 TC-004 — Happy path — flag named *.zip.flag with no companion .zip

**Type:** Happy Path  |  **Priority:** High

**Objective:** Flag uses the .zip.flag convention and no .zip archive is written.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Run an export with failures. | `customer populated; process_date=20260313` | Run completes. |
| 2 | Inspect the feedback prefix object names. | `List feedback/20260313/` | envelope_error_20260313.zip.flag exists; there is NO envelope_error_20260313.zip object next to it. |
| 3 | Confirm flag body is plain text. | `Read the flag object` | Body is plain text (not a zip archive). |

---

### 🟣 TC-005 — Security/Routing — flag treated as non-zip by outbound handler

**Type:** Security  |  **Priority:** Medium

**Objective:** Outbound PGP/zip routing keys off '.zip' suffix; '.zip.flag' must be excluded.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Apply the outbound routing rule that selects keys ending with '.zip'. | `Routing predicate: key.endswith('.zip')` | Predicate is exercised against the run's objects. |
| 2 | Evaluate the predicate against the flag key. | `Key: .../envelope_error_20260313.zip.flag` | Predicate is FALSE (key ends with '.flag'); the flag is NOT selected as a zip payload. |
| 3 | Confirm the flag follows the non-zip handling branch. | `Trace handling` | Flag is handled like other non-.zip objects (not PGP-zipped). |

---

### 🔴 TC-006 — Negative — re-run does not duplicate single keys

**Type:** Negative  |  **Priority:** Medium

**Objective:** Re-running for the same date yields one object per filename (overwrite, not duplicate).

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Run the export twice for the same date. | `Two runs, process_date=20260313, same sources` | Both runs complete. |
| 2 | Enumerate data/flag objects. | `List keys for 20260313` | Each filename exists exactly once (single object per filename); no duplicate/suffixed variants. |

---

_Generated for the DXV Feedback (Quarantine Export) integration test suite — 2026-06-11._
