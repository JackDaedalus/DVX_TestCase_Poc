---
jira_issue_type: "Story"
story_key: "DXV-FRE-003"
summary: "Resolve, normalise and prefix output object paths correctly"
epic: "Output Layout & Object Keys"
priority: "High"
story_points: 5
components: ["failed-record-export"]
labels: ["dxv", "failed-record-export", "minio", "paths", "org-unit", "integration"]
status: "Ready for Test"
test_case_count: 5
test_type_breakdown: {"Happy Path": 3, "Boundary": 1, "Negative": 1}
---

# DXV-FRE-003 — Resolve, normalise and prefix output object paths correctly

> **Epic:** Output Layout & Object Keys  |  **Product:** DXV — Data Exchange Vault  |  **Pipeline:** `failed-record-export`

## Story Details

| Field | Value |
| --- | --- |
| **Story Key** | `DXV-FRE-003` |
| **Issue Type** | Story |
| **Epic** | Output Layout & Object Keys |
| **Priority** | **High** |
| **Story Points** | 5 |
| **Components** | `failed-record-export` |
| **Labels** | `dxv` `failed-record-export` `minio` `paths` `org-unit` `integration` |
| **Status** | Ready for Test |

## User Story

> **As a** platform integration engineer  
> **I want** the exporter to place every object under predictable, normalised roots and to prepend the ORG_UNIT segment when configured  
> **so that** downstream DXV / SFTP tooling can reliably watch and pick up files using stable, lowercase, slash-clean keys that match typical DXV / NROD layouts.

## Description

Output objects are written under three configurable roots: bad_records_location (clean rows for resubmit), feedback_location (flags/triggers) and report_location (aggregated + detailed reports). The built-in defaults are landing/acquisition/bad, landing/acquisition/feedback and landing/acquisition/feedback/reporting respectively.

Configured roots are normalised before use: leading/trailing slashes are stripped and the value is lowercased, so behaviour matches typical DXV / NROD SFTP layouts. Full object keys are under the bucket.

If the ORG_UNIT environment variable is set, the exporter prepends {ORG_UNIT}/ to the path before the configured roots. If ORG_UNIT is unset, the roots sit directly under the bucket. Object name patterns embed process_date and table_name (for example {bad_records_location}/{process_date}/{table_name}_{process_date}.{ext}).

## Key Terms & Behaviour

| Term | Behaviour / Definition |
| --- | --- |
| **Default bad root** | landing/acquisition/bad |
| **Default feedback root** | landing/acquisition/feedback |
| **Default report root** | landing/acquisition/feedback/reporting |
| **Normalisation** | Strip leading/trailing slashes and lowercase the configured roots. |
| **ORG_UNIT prefix** | When set, {ORG_UNIT}/ is prepended BEFORE the configured roots. |
| **Clean bad pattern** | {bad_records_location}/{process_date}/{table_name}_{process_date}.{ext} |
| **Aggregated pattern** | {report_location}/{process_date}/aggregated_{table_name}_{process_date}.{ext} |
| **Detailed pattern** | {report_location}/{process_date}/detailed_{table_name}_{process_date}.{ext} |

## Acceptance Criteria

**Definition of Done**

1. With no overrides and ORG_UNIT unset, objects land under the three documented default roots directly beneath the bucket.
2. A configured root with surrounding slashes and mixed case is normalised (slashes stripped, lowercased) before keys are built.
3. When ORG_UNIT is set, every object key is prefixed with {ORG_UNIT}/ ahead of the configured root.
4. Object names exactly follow the documented patterns, embedding process_date and table_name with the correct {ext}.
5. Overriding one root does not move objects belonging to the other roots.

## Recommended Test Data

| Artefact | Example Value / Format |
| --- | --- |
| **ORG_UNIT (set)** | `OrgA  ->  prefix 'orga/' after normalisation considerations` |
| **Un-normalised root** | `'/Landing/Acquisition/Bad/'  ->  'landing/acquisition/bad'` |
| **process_date** | `20260313` |
| **table_name** | `customer` |
| **ext** | `csv (from file_format)` |
| **Expected clean-bad key** | `landing/acquisition/bad/20260313/customer_20260313.csv` |
| **Expected aggregated key** | `landing/acquisition/feedback/reporting/20260313/aggregated_customer_20260313.csv` |

## Global Preconditions

- A populated quarantine table exists for the table/date under test.
- ORG_UNIT is explicitly set or unset per the individual test case.

## Test Cases

**Coverage:** 5 test case(s) — 🟢 Happy Path × 3  🟠 Boundary × 1  🔴 Negative × 1

---

### 🟢 TC-001 — Happy path — default roots, ORG_UNIT unset

**Type:** Happy Path  |  **Priority:** High

**Objective:** All objects land under the documented default roots with correct names.

**Preconditions:**
- ORG_UNIT is unset / empty.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Run the export with no path kwargs and no spec overrides. | `process_date=20260313; file_format=csv; table=customer` | Run completes. |
| 2 | Verify the clean-bad key. | `Expect landing/acquisition/bad/20260313/customer_20260313.csv` | Object exists at exactly that key. |
| 3 | Verify the aggregated and detailed keys. | `Expect .../feedback/reporting/20260313/aggregated_customer_20260313.csv and detailed_...` | Both objects exist at the documented report paths. |
| 4 | Verify the feedback flag key. | `Expect landing/acquisition/feedback/20260313/<flag>` | Flag object exists under the feedback root. |

---

### 🟢 TC-002 — Happy path — ORG_UNIT prefix applied

**Type:** Happy Path  |  **Priority:** High

**Objective:** Setting ORG_UNIT prepends {ORG_UNIT}/ before the configured roots for every object.

**Preconditions:**
- ORG_UNIT=OrgA

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Set ORG_UNIT and run the export with default roots. | `ORG_UNIT=OrgA; process_date=20260313; table=customer` | Run completes. |
| 2 | Verify keys are prefixed. | `Expect <orgunit-prefix>/landing/acquisition/bad/20260313/customer_20260313.csv` | Every object key begins with the ORG_UNIT segment ahead of the configured root. |
| 3 | Confirm prefix is applied consistently to all three roots + flags. | `Inspect bad, report and feedback keys` | All carry the same ORG_UNIT prefix. |

---

### 🟠 TC-003 — Boundary/Normalisation — un-normalised configured roots

**Type:** Boundary  |  **Priority:** High

**Objective:** Roots with surrounding slashes and uppercase are normalised before keys are built.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Override roots with messy values. | `bad_records_location='/Landing/Acquisition/Bad/'` | Accepted by config. |
| 2 | Run the export. | `process_date=20260313; table=customer` | Run completes. |
| 3 | Verify the resulting key is normalised. | `Expect landing/acquisition/bad/20260313/customer_20260313.csv` | Leading/trailing slashes stripped and value lowercased; no doubled '//' or mixed case in the key. |

---

### 🟢 TC-004 — Happy path — selective root override isolation

**Type:** Happy Path  |  **Priority:** Medium

**Objective:** Overriding one root does not relocate objects for the other roots.

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Override only the report root. | `report_location='landing/acquisition/custom_reporting'` | Config accepted. |
| 2 | Run the export. | `process_date=20260313; table=customer` | Run completes. |
| 3 | Verify report objects moved but bad/feedback did not. | `Inspect all three roots` | aggregated/detailed under custom_reporting; clean-bad still under landing/acquisition/bad; flag still under landing/acquisition/feedback. |

---

### 🔴 TC-005 — Negative — overlapping/empty root values

**Type:** Negative  |  **Priority:** Low

**Objective:** Empty or degenerate root overrides are handled predictably (no keys with leading slash or empty segment).

| # | Test Step / Action | Test Data (format / value) | Expected Result |
| :---: | --- | --- | --- |
| 1 | Override a root with an empty string. | `bad_records_location=''` | Config accepted or rejected — behaviour is documented and deterministic. |
| 2 | Run the export and inspect keys. | `process_date=20260313; table=customer` | No object key is produced with a leading '/' or an empty path segment (e.g. never '//20260313/...'). |

---

_Generated for the DXV Feedback (Quarantine Export) integration test suite — 2026-06-11._
