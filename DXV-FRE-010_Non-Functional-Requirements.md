---
jira_issue_type: "Story"
story_key: "DXV-FRE-010"
summary: "Validate non-functional qualities of the quarantine export stage"
epic: "Non-Functional Quality"
priority: "High"
story_points: 8
components: ["failed-record-export"]
labels: ["dxv", "failed-record-export", "non-functional", "performance", "security", "reliability"]
status: "Ready for Test"
test_case_count: 8
test_type_breakdown: {"Non-Functional": 6, "Security": 2}
---

# DXV-FRE-010 — Validate non-functional qualities of the quarantine export stage

> **Epic:** Non-Functional Quality  |  **Product:** DXV — Data Exchange Vault  |  **Pipeline:** `failed-record-export`

## Story Details

| Field | Value |
| --- | --- |
| **Story Key** | `DXV-FRE-010` |
| **Issue Type** | Story |
| **Epic** | Non-Functional Quality |
| **Priority** | **High** |
| **Story Points** | 8 |
| **Components** | `failed-record-export` |
| **Labels** | `dxv` `failed-record-export` `non-functional` `performance` `security` `reliability` |
| **Status** | Ready for Test |

## User Story

> **As a** Test Engineering Manager  
> **I want** the export stage to meet performance, scalability, reliability/idempotency, security and compatibility expectations under realistic conditions  
> **so that** the quarantine feedback loop is dependable and safe at production scale, not just functionally correct on small inputs.

## Description

Beyond functional correctness, the failed-record-export stage must behave well under production conditions. This story groups the non-functional checks: throughput and latency on large quarantine volumes, scaling across many contract tables, idempotent re-runs for the same process_date, resilience to transient MinIO/Iceberg errors, security of credentials and the outbound PGP routing contract, and backwards compatibility with DXV / NetReveal naming.

These tests rely on the documented behaviours of the stage (single object per filename, unconditional .keep markers, *.zip.flag naming, shared flow-wide credentials, and the one-flag-per-run envelope rule) and assert the quality attributes around them.

Targets below are representative acceptance thresholds for the suite; calibrate the exact numbers to the deployment's SLAs before execution.

## Key Terms & Behaviour

| Term | Behaviour / Definition |
| --- | --- |
| **Performance** | Time to export a large quarantine volume within an agreed window. |
| **Scalability** | Behaviour as the number of contract tables and total rows grows. |
| **Reliability/Idempotency** | Re-running the same date converges to one object per filename. |
| **Security** | Credential handling and the .zip-suffix outbound routing contract. |
| **Compatibility** | DXV / NetReveal-compatible flag naming and trigger payloads. |
| **Observability** | The returned summary dict and logs make outcomes auditable. |

## Acceptance Criteria

**Definition of Done**

1. A large single-table quarantine export completes within the agreed performance window and memory budget.
2. Throughput scales acceptably as the number of contract tables increases (no super-linear degradation).
3. Re-running the same process_date is idempotent: one object per filename, consistent flag outcome.
4. Transient MinIO/Iceberg errors are retried or fail cleanly without leaving partial/duplicate objects.
5. Credentials are never written into exported objects, flags, logs or object keys.
6. Outbound routing keyed on '.zip' never selects '*.zip.flag' objects (handled as non-zip).
7. Flag naming remains DXV/NetReveal compatible and the acq_success payload is a single newline.

## Recommended Test Data

| Artefact | Example Value / Format |
| --- | --- |
| **Large volume** | `1,000,000 quarantine rows in one table` |
| **Many tables** | `50 contract tables for one process_date` |
| **Perf target (example)** | `<= 10 min wall-clock; stable, bounded memory` |
| **Retry scenario** | `Inject transient 5xx / connection reset on MinIO put` |
| **Sensitive values** | `MinIO access key / secret must never appear in outputs` |
| **process_date** | `20260313` |

## Global Preconditions

- A representative non-prod environment sized close to production.
- Ability to seed large quarantine volumes and to inject transient object-store faults.
- Agreed SLA thresholds to assert against (substitute real numbers for the examples).

## Test Cases

**Coverage:** 8 test case(s) — 🔵 Non-Functional × 6  🟣 Security × 2

---

### 🔵 TC-001 — Performance — large single-table export within window

**Type:** Non-Functional  |  **Priority:** High

**Objective:** Exporting a very large quarantine table meets the agreed time/memory budget.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Seed a large quarantine table. | `customer: 1,000,000 rows with mixed validation_errors` | Table populated at scale. |
| 2 | Run the export and measure wall-clock + peak memory. | `process_date=20260313; capture timing & memory` | Run completes within the agreed window (example <= 10 min) with bounded memory (no OOM). |
| 3 | Verify output completeness. | `Counts in bad/detailed vs source; aggregated totals` | All rows accounted for; aggregated counts reconcile to source. |

---

### 🔵 TC-002 — Scalability — many contract tables in one run

**Type:** Non-Functional  |  **Priority:** Medium

**Objective:** Throughput degrades at most linearly as table count grows.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Seed many tables with moderate row counts. | `50 tables x ~10k rows each; process_date=20260313` | All tables populated. |
| 2 | Run the export and record per-table and total timing. | `Measure total + per-table durations` | Total time scales ~linearly with table count; no pathological slowdown or memory growth. |
| 3 | Verify all tables exported and one flag emitted. | `List objects; inspect flag` | Each table has its files; exactly one envelope_error flag aggregates all failing tables. |

---

### 🔵 TC-003 — Reliability — idempotent re-run for same date

**Type:** Non-Functional  |  **Priority:** High

**Objective:** Re-running the same process_date does not duplicate objects or flip the flag.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Run the export once and snapshot the object listing. | `process_date=20260313; record keys + checksums` | Baseline captured. |
| 2 | Re-run the export with identical inputs. | `process_date=20260313 again` | Run completes. |
| 3 | Compare object listings. | `Diff keys vs baseline` | Same set of keys (one object per filename); .keep markers and flag outcome unchanged. |

---

### 🔵 TC-004 — Reliability — transient object-store fault handling

**Type:** Non-Functional  |  **Priority:** High

**Objective:** A transient MinIO error does not leave partial or duplicate objects.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Inject a transient fault during writes. | `Simulate 5xx / connection reset on a subset of put operations` | Fault injected. |
| 2 | Run the export. | `process_date=20260313` | Stage retries or fails cleanly (documented behaviour). |
| 3 | Inspect resulting object state. | `List keys; verify integrity` | No partially-written/duplicate objects remain; on success, one object per filename; on clean failure, state is recoverable by re-run. |

---

### 🟣 TC-005 — Security — no credential leakage into outputs

**Type:** Security  |  **Priority:** Highest

**Objective:** MinIO credentials never appear in objects, flags, keys or logs.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Run the export with known credential values configured. | `Access key / secret set to recognisable sentinel values` | Run completes. |
| 2 | Scan all outputs and logs for the sentinels. | `grep object bodies, flag bodies, object keys, run logs` | Sentinel credential values are NOT present anywhere in outputs or logs. |

---

### 🟣 TC-006 — Security — outbound PGP routing excludes *.zip.flag

**Type:** Security  |  **Priority:** High

**Objective:** The '.zip'-suffix outbound branch must not select flag objects.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Run an export that emits a flag. | `process_date=20260313 with failures` | envelope_error_20260313.zip.flag written. |
| 2 | Apply the outbound selection rule keyed on '.zip'. | `Predicate: path ends with '.zip'` | Flag key ends with '.flag' -> predicate FALSE; flag is not PGP/zip-routed. |

---

### 🔵 TC-007 — Compatibility — DXV/NetReveal naming & trigger payload

**Type:** Non-Functional  |  **Priority:** Medium

**Objective:** Flag names and acq_success payload remain backwards compatible.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Run both a clean and a failing scenario. | `One run no failures, one run with failures; process_date=20260313` | Both complete. |
| 2 | Verify flag names match the DXV/NetReveal convention. | `acq_success_20260313.zip.flag and envelope_error_20260313.zip.flag` | Names match exactly; *.zip.flag convention preserved. |
| 3 | Verify the acq_success payload. | `Read success flag bytes` | Body is exactly a single newline (trigger compatibility preserved). |

---

### 🔵 TC-008 — Observability — auditable run summary

**Type:** Non-Functional  |  **Priority:** Medium

**Objective:** The returned dict and logs make the run outcome auditable.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Run a mixed scenario and capture return value + logs. | `Some tables fail, some skipped; process_date=20260313` | Run completes. |
| 2 | Review the summary and logs. | `result dict + log lines` | Outcome is auditable: which tables exported/skipped, object counts, and which flag was emitted are all discernible. |

---

_Generated for the DXV Feedback (Quarantine Export) integration test suite — 2026-06-11._
