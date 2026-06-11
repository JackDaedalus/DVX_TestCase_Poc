# Feedback (quarantine export)

Exports the following items to MinIO:
 - validation failures from Iceberg quarantine tables as delimiter-separated files
 - acquisition success or error (envelope) flag files

The run uses the same data contract and **`process_date`** (`YYYYMMDD`) as the rest of the AML flow for that execution.

## At a glance

- **Pipeline:** `failed-record-export` (same **`run_pipeline`** pattern as other AML stages).
- **Reads:** Iceberg quarantine tables for tables listed in the contract and the run’s **`process_date`** — rows that already failed **`data-validation`**.
- **Writes:** Data files (clean resubmit copy, summary report, full detail) plus flag files on MinIO, for human review and file-based automation.
- **Defaults:** Under the bucket, the built-in layout starts at **`landing/acquisition/...`** unless kwargs or optional spec fields override the roots ([Where files land](#where-files-land-default-layout)).

## Run it

You need the bucket-relative path to the data contract JSON and the run **`process_date`**. Path roots and delimiter/header behaviour otherwise come from the merged **parsed spec** and built-in defaults ([Parsed spec: export-related settings](#data-contract-fields-export-related), [Where files land](#where-files-land-default-layout)).

```python
import os
from pipeline import run_pipeline

# Bucket-relative path to the data contract JSON — use a distinct name from
# json-transformation’s `config_path` / `CONFIG_PATH` (table-to-JSON config).
minio_config_path = os.getenv("minio_config_path")
process_date = os.getenv("process_date")

result = run_pipeline(
    "failed-record-export",
    minio_config_path=minio_config_path,
    process_date=process_date,
)
```

Optional **`run_pipeline`** keyword arguments (same names as optional spec fields): `bad_records_location`, `feedback_location`, `report_location`, `file_format`, `separator`, `include_header`.

**Precedence:** kwargs → optional fields in the spec JSON → built-in defaults.

## Where files land (default layout)

Configured roots are **normalised** (strip slashes, **lowercase**) so behaviour matches typical **DXV / NROD SFTP** layouts. In the path patterns below, substitute your effective roots if you override the defaults.

Full object keys are **under the bucket**. 

If **`ORG_UNIT`** is set, the exporter prepends **`{ORG_UNIT}/`** to the path **before** the configured roots.

If unset, the roots below sit directly under the bucket. 

**Built-in** roots (the segment after that optional prefix) are:

| Role | Default root path (does not include `ORG_UNIT`) |
| ---- | ----------------------------------------------- |
| **Clean rows for resubmit** (validation JSON columns removed) | `landing/acquisition/bad` |
| **Feedback / flags** (DXV-style triggers) | `landing/acquisition/feedback` |
| **Reports** (aggregated + full quarantine export) | `landing/acquisition/feedback/reporting` |

**Object patterns** (`{ext}` follows export `file_format`, supported values are `csv` and `txt`):

| What you get | Path pattern |
| ------------ | ------------ |
| Clean bad rows | `{bad_records_location}/{process_date}/{table_name}_{process_date}.{ext}` |
| Aggregated summary (counts by error type / field) | `{report_location}/{process_date}/aggregated_{table_name}_{process_date}.{ext}` |
| Full quarantine export (includes `validation_errors` as JSON on rows) | `{report_location}/{process_date}/detailed_{table_name}_{process_date}.{ext}` |
| Acquisition success flag | `{feedback_location}/{process_date}/acq_success_{process_date}.zip.flag` |
| Acquisition / validation error flag | `{feedback_location}/{process_date}/envelope_error_{process_date}.zip.flag` |

**One flag per run:** **`acq_success_*.zip.flag`** when **no** quarantine rows were exported; **`envelope_error_*.zip.flag`** when **any** table had failures (DXV-compatible naming).

## Inputs and outputs

| Input | Format | Notes |
| ----- | ------ | ----- |
| **Data contract JSON** | JSON in MinIO | `minio_config_path`, `process_date`. |
| **Quarantine Iceberg tables** | Iceberg | One per **`table_name`** in **`tables[]`** for the run date; naming under [Behaviour](#behaviour-quarantine-sources-and-paths). |
| **Optional kwargs** | Strings / flags | Override export roots and delimiter/header behaviour ([Run it](#run-it)). |
| **`ORG_UNIT`** (env) | Optional string | Prefix on failed-record export paths when enabled for the deployment. |

| Output | Format | Notes |
| ------ | ------ | ----- |
| **MinIO objects** | Delimiter-separated files, **flag** files, and **three `.keep` markers per run** (always) | Layout: [Where files land](#where-files-land-default-layout). Naming details: [Storage behaviour](#storage-behaviour-and-naming-edge-cases). |
| **Return value** | Python `dict` | Summary returned by the pipeline runner for this stage. |

## File contents (data exports and flags)

The three **data** exports use one writer contract (delimiter + header from the spec). **Flags** are separate plain-text objects.

### Data files (bad, aggregated, detailed)

| Export | Content |
| ------ | ------- |
| **Clean bad** | Same rows as quarantine but **`validation_errors`** and **`validation_timestamp`** are **dropped** for clean resubmit. |
| **Aggregated** | Counts per **`(error_type, field_name)`** after exploding **`validation_errors`**. If every row has an empty or null errors array, the exporter writes **one fallback summary row** (`validation_error`, empty field, **total row count**) so the file is not header-only—aligned with the envelope flag when errors cannot be exploded. |
| **Detailed** | Full row set with **`validation_errors`** as **JSON** on each row. |

### `envelope_error_{YYYYMMDD}.zip.flag`

Body is **text**, one failure summary per line:

`{table_name}_{DDMMYYYY}, {reason}, {count}`

- **First column:** logical table name and processing date in **`DDMMYYYY`** (example: `customer_13032026` for 13 March 2026).
- **Reason:** from the validation result (**`error_type`** and **`field_name`**, space-separated). If **`validation_errors`** cannot be exploded for that table, a **single fallback line** uses the row **count** instead.

### `acq_success_{YYYYMMDD}.zip.flag`

Body is a **single newline** for DXV-style trigger compatibility; treat the exact payload as part of your integration contract with downstream pickup.

## Export formats vs ingest

- **Ingest** allows **`input.extension`** **`csv`** / **`txt`** only on object names in MinIO.
- **`input.extension`** and **`input.delimiter`** in the contract **seed** export **`file_format`** and **`separator`** unless you set top-level overrides.
- **Export-only** top-level **`file_format`** values **`pipe`** and **`gs`**: use when export keys must differ from ingest (for example uploads with `"input": { "extension": "csv", "delimiter": "|" }` and export `"file_format": "pipe"` so keys use **`.pipe`**). For **`.csv` keys** with pipe-separated content, use **`"file_format": "csv"`** and **`"separator": "|"`**.
- **`txt`** export defaults to **tab** if no separator is set.

| Setting | Where it is set | Purpose |
| ------- | --------------- | ------- |
| `process_date` | **`run_pipeline(..., process_date=...)`** only (merged into parsed spec) | Run date **`YYYYMMDD`**; required on every run, same as other MinIO-driven stages. |
| `tables[]` | **Contract JSON** | Logical **`table_name`** entries whose quarantine Iceberg tables are export sources for that date. |
| `input.extension` / `input.delimiter` | **Contract JSON** | Ingest settings; also **seed** export **`file_format`** / **`separator`** unless overridden. |
| `file_format` | **Top-level contract JSON** and/or matching **`run_pipeline`** kwargs | Optional **`csv`**, **`txt`**, **`pipe`**, **`gs`**. |
| `separator` | **Top-level contract JSON** and/or matching **`run_pipeline`** kwargs | Export delimiter; **`pipe`** / **`gs`** fix the separator in the writer. |
| `include_header` | **Top-level contract JSON** and/or matching **`run_pipeline`** kwargs | Boolean, default **`true`**. |
| `bad_records_location` | **Top-level contract JSON** and/or matching **`run_pipeline`** kwargs | Optional override of the default bad root. |
| `feedback_location` | **Top-level contract JSON** and/or matching **`run_pipeline`** kwargs | Optional override of the default feedback root. |
| `report_location` | **Top-level contract JSON** and/or matching **`run_pipeline`** kwargs | Optional override of the default report root. |

#### RFFilespec (`use_rffilespec`) and headers
When **`input.use_rffilespec`** is **`true`**, ingest uses **headerless** RFFilespec/XML-driven column order. Failed-record export still defaults **`include_header`** to **`true`** unless you set it—so for **headerless** bad rows and reports that match that ingest shape, set **`include_header`** to **`false`** in the **contract JSON** or pass **`include_header=False`** to **`run_pipeline`**. Export **path roots** stay **global** for this stage (`bad_records_location`, `feedback_location`, `report_location`); there is no separate per-table export path layout.

## Behaviour (quarantine sources and paths)

- **Quarantine table name:** `{CATALOG}.{WORKSPACE_ID}.quarantine_{table_name}_{process_date}` (workspace/catalog from environment; see [AML Data flows overview](index.md#internal-environment-variables-workspace-catalog)).
- **Missing table:** if a quarantine table for a contract table does not exist for that date, that table is **skipped** (for example no failed rows for that table/date, or quarantine was already dropped)—not a hard failure for the whole export.
- **Path roots:** precedence and **normalisation** are covered in [Run it](#run-it) and [Where files land](#where-files-land-default-layout).

## Storage behaviour and naming edge cases

- **Prefix markers (`.keep`):** every run writes **three** zero-byte **`.keep`** objects—under **`{bad_records_location}/{process_date}/`**, **`{report_location}/{process_date}/`**, and **`{feedback_location}/{process_date}/`** (after any **`ORG_UNIT`** prefix)—**before** per-table exports. They are not conditional on quarantine rows; they ensure each date prefix exists as a concrete object-store key for downstream tooling.
- **Single keys:** bad, aggregated, detailed, and flag objects are written at the **documented paths** as **one object per filename**

### Why `*.zip.flag` without a companion `.zip`?

The **`.zip` in the filename** is a **DXV convention**, **backwards compatible with NetReveal** naming (flags paired by basename with historical **`envelope_*.zip`** flows). **This stage does not write a `.zip` archive** next to those flags: bad rows and reports are **delimiter-separated files**, and **flag bodies are plain text**—the `.zip` segment is **only** in the object name for integration compatibility.

**Outgoing PGP (typical DXV / reference integration behaviour):** handlers that encrypt **outbound** files often key off the path **ending with `.zip`**. **`acq_success_*`** and **`envelope_error_*`** objects are named **`*.zip.flag`**, so the path **ends with `.flag`**, not **`.zip`**—they are **not** treated as zip payloads for that branch and are handled like other **non-`.zip`** objects.

For **routing, archiving, org-specific keys, and DXV UI configuration**, see [DXV (Data Exchange Vault) alignment](#dxv-data-exchange-vault-alignment) below and your organisation’s NetReveal Confluence runbooks.

### Ingest alignment

**`ingest-to-staging`** resolves each table’s upload from the **exact** object key **`{table_name}_{process_date}.{input.extension}`** under your ingest prefix. If your filenames differ, rename objects or adjust **`process_date`** / the contract so the key matches.

## Integration

- **MinIO bucket and credentials** use the **same flow-wide** settings as other MinIO-driven stages (for example ingest and validation).
- **DXV** (or a similar pickup service) must **watch or move** the roots you use (for example **`landing/acquisition/feedback/`** and **`landing/acquisition/bad/`** with defaults).
- **Archiving** of picked-up files is **downstream** on the DXV side, not part of this stage.

## Example (explicit defaults)

Same as [Run it](#run-it), with roots spelled out to match built-in defaults—useful when a runbook always sets paths explicitly.

```python
import os
from pipeline import run_pipeline

minio_config_path = os.getenv("minio_config_path")
process_date = os.getenv("process_date")

result = run_pipeline(
    "failed-record-export",
    minio_config_path=minio_config_path,
    bad_records_location="landing/acquisition/bad",
    feedback_location="landing/acquisition/feedback",
    report_location="landing/acquisition/feedback/reporting",
    # file_format="pipe",
    # separator="|",
    include_header=True,
    process_date=process_date,
)
```

## Related topics

- [AML Data flows overview](index.md) — registered pipelines and common kwargs
- [Validation](validation.md) — how rows reach quarantine
- [Ingestion](ingestion.md) — staging keys and contract-driven ingest
- [Data contract JSON Schema](../data-contracts/json-schema.md) — root schema and optional export keys