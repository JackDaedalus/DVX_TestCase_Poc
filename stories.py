# -*- coding: utf-8 -*-
"""
Single source of truth for the DXV Feedback (Quarantine Export) test suite.

Every entry in ``STORIES`` is a dict with this schema (consumed identically by
the Word and Markdown renderers):

    {
      "id":            "DXV-FRE-001",          # JIRA-style key
      "filename":      "DXV-FRE-001_...",      # output basename (no extension)
      "title":         "Short imperative title",
      "epic":          "Epic / component name",
      "labels":        ["dxv", "export", ...], # JIRA labels
      "priority":      "High",                 # Highest|High|Medium|Low
      "story_points":  5,
      "components":    ["failed-record-export"],
      "persona":       "AML data engineer",
      "want":          "<the 'I want' clause>",
      "benefit":       "<the 'so that' clause>",
      "description":   "Long narrative (list of paragraph strings)",
      "context":       [ ("Term", "explanation"), ... ],   # optional definitions
      "acceptance":    [ "AC1 ...", "AC2 ...", ... ],
      "test_data":     [ ("Artefact", "Example value/format"), ... ],
      "preconditions": [ "global precondition strings" ],
      "tests": [
          {
            "id":   "TC-001",
            "title":"...",
            "type": "Happy Path|Negative|Boundary|Non-Functional|Security",
            "priority": "High",
            "objective": "one-line goal",
            "preconditions": ["case-specific preconditions"],   # optional
            "steps": [
                {"action": "...", "data": "...", "expected": "..."},
                ...
            ],
            "postconditions": ["..."],   # optional
          },
          ...
      ],
    }
"""

# ===========================================================================
# Suite-level metadata (used by the overview / epic document)
# ===========================================================================
SUITE = {
    "product": "DXV — Data Exchange Vault",
    "module": "AML Data Ingestion · Feedback (Quarantine Export)",
    "pipeline": "failed-record-export",
    "epic_key": "DXV-FRE",
    "version": "1.0",
    "author": "Software Test Engineering",
    "summary": (
        "Integration test suite for the DXV failed-record-export pipeline stage. "
        "This stage exports validation failures from Iceberg quarantine tables to "
        "MinIO as delimiter-separated files, together with acquisition success / "
        "error envelope flag files, using the same data contract and process_date "
        "as the wider AML flow. The suite below decomposes the stage into discrete "
        "functional and non-functional areas, each captured as an Agile User Story "
        "with executable, data-driven test cases."
    ),
    "in_scope": [
        "Pipeline invocation, parameter resolution and configuration precedence.",
        "Reading Iceberg quarantine tables and per-table iteration / skip behaviour.",
        "Output path resolution, normalisation and ORG_UNIT prefixing.",
        "Generation of the three data exports (clean bad, aggregated, detailed).",
        "Envelope flag-file semantics (acq_success vs envelope_error).",
        "Export format, delimiter and header handling (csv/txt/pipe/gs).",
        "RFFilespec headerless alignment.",
        "Storage behaviour, .keep markers and *.zip.flag naming conventions.",
        "Downstream DXV integration and ingest-key alignment.",
        "Non-functional qualities: performance, reliability, security, compatibility.",
    ],
    "out_of_scope": [
        "Upstream data-validation logic that places rows into quarantine.",
        "DXV-side archiving and routing of picked-up files.",
        "Outbound PGP encryption implementation (only its file-selection contract).",
        "Provisioning of MinIO / Iceberg infrastructure.",
    ],
    "env": [
        ("Object store", "MinIO (flow-wide bucket + credentials)"),
        ("Table format", "Apache Iceberg quarantine tables"),
        ("Runner", "pipeline.run_pipeline(\"failed-record-export\", ...)"),
        ("Key env vars", "ORG_UNIT (optional), WORKSPACE_ID, CATALOG"),
        ("Process date", "process_date in YYYYMMDD"),
    ],
}


# Convenience builders to keep step authoring terse and consistent. ----------
def step(action, data, expected):
    return {"action": action, "data": data, "expected": expected}


STORIES = []


# ===========================================================================
# DXV-FRE-001 — Pipeline invocation & parameter resolution
# ===========================================================================
STORIES.append({
    "id": "DXV-FRE-001",
    "filename": "DXV-FRE-001_Pipeline-Invocation-and-Parameter-Resolution",
    "title": "Invoke the failed-record-export pipeline with correct parameter resolution",
    "epic": "Pipeline Orchestration & Configuration",
    "labels": ["dxv", "failed-record-export", "pipeline", "configuration", "integration"],
    "priority": "Highest",
    "story_points": 5,
    "components": ["failed-record-export"],
    "persona": "AML data engineer",
    "want": (
        "to trigger the failed-record-export stage through run_pipeline using a data "
        "contract path and a process_date, with optional keyword overrides"
    ),
    "benefit": (
        "the quarantine export runs deterministically for the correct AML execution "
        "date and honours the documented configuration precedence"
    ),
    "description": [
        "The failed-record-export stage is invoked exactly like the other AML stages, "
        "via the shared run_pipeline runner. The caller supplies the bucket-relative "
        "path to the data contract JSON (minio_config_path) and the run's process_date "
        "in YYYYMMDD. All other behaviour — export path roots, delimiter and header "
        "handling — is resolved from a merged configuration.",
        "Configuration is resolved with a strict precedence: run_pipeline keyword "
        "arguments take priority, then optional fields in the spec (contract) JSON, "
        "then the built-in defaults. The optional kwargs share the same names as the "
        "optional spec fields: bad_records_location, feedback_location, report_location, "
        "file_format, separator and include_header.",
        "On completion the runner returns a Python dict summarising the stage. The "
        "minio_config_path used here must be a distinct name from json-transformation's "
        "config_path / CONFIG_PATH (which is the table-to-JSON config), and process_date "
        "is supplied only through run_pipeline(..., process_date=...) — it is then merged "
        "into the parsed spec.",
    ],
    "context": [
        ("minio_config_path", "Bucket-relative path to the data contract JSON; required."),
        ("process_date", "Run date in YYYYMMDD; required on every run, supplied only via run_pipeline."),
        ("Precedence", "kwargs -> optional fields in spec JSON -> built-in defaults."),
        ("Optional kwargs", "bad_records_location, feedback_location, report_location, file_format, separator, include_header."),
        ("Return value", "Python dict summary returned by the pipeline runner for this stage."),
    ],
    "acceptance": [
        "GIVEN a valid contract path and process_date, WHEN run_pipeline(\"failed-record-export\", ...) is called, THEN the stage executes and returns a summary dict.",
        "A kwarg value overrides the same optional field in the spec JSON, which in turn overrides the built-in default.",
        "process_date supplied via run_pipeline is merged into the parsed spec and used for all quarantine table names and output paths.",
        "Omitting a required parameter (minio_config_path or process_date) fails fast with a clear error and writes no output objects.",
        "The pipeline name string must be exactly \"failed-record-export\"; an unknown name is rejected.",
    ],
    "test_data": [
        ("minio_config_path", "config/aml/customer_contract.json"),
        ("process_date (valid)", "20260313"),
        ("process_date (invalid)", "2026-03-13, 13032026, 20261332, '', null"),
        ("file_format kwarg", "csv | txt | pipe | gs"),
        ("separator kwarg", "',' | '|' | '\\t'"),
        ("include_header kwarg", "True | False"),
        ("Pipeline name", "failed-record-export"),
    ],
    "preconditions": [
        "MinIO bucket and credentials are configured flow-wide and reachable.",
        "A valid data contract JSON exists at the bucket-relative path under test.",
        "Quarantine Iceberg tables exist for at least one contract table for the chosen process_date (unless a test states otherwise).",
    ],
    "tests": [
        {
            "id": "TC-001",
            "title": "Happy path — minimal valid invocation",
            "type": "Happy Path",
            "priority": "Highest",
            "objective": "Confirm the stage runs with only the two required parameters and returns a summary dict.",
            "steps": [
                step("Set environment variables for the run.",
                     "minio_config_path=config/aml/customer_contract.json; process_date=20260313",
                     "Variables are accepted; no error raised."),
                step("Call run_pipeline with the pipeline name and the two required params.",
                     "run_pipeline(\"failed-record-export\", minio_config_path=..., process_date=\"20260313\")",
                     "Stage starts and reads the contract JSON successfully."),
                step("Wait for the run to complete and capture the return value.",
                     "result = <return of run_pipeline>",
                     "run_pipeline returns a Python dict (not None / not an exception)."),
                step("Inspect the returned summary dict.",
                     "result keys/values",
                     "Dict summarises the stage execution (e.g. tables processed, objects written, flag emitted)."),
            ],
            "postconditions": [
                "Output objects are written under the default roots for process_date 20260313.",
            ],
        },
        {
            "id": "TC-002",
            "title": "Happy path — kwargs override spec fields",
            "type": "Happy Path",
            "priority": "High",
            "objective": "Verify run_pipeline kwargs take precedence over the equivalent optional fields in the spec JSON.",
            "steps": [
                step("Prepare a contract JSON that sets optional fields to known values.",
                     "spec: file_format=\"csv\", separator=\",\", include_header=true",
                     "Contract is valid and parseable."),
                step("Invoke run_pipeline overriding the same fields via kwargs.",
                     "file_format=\"pipe\", separator=\"|\", include_header=False, process_date=\"20260313\"",
                     "Run completes successfully."),
                step("Examine the written object keys and file contents.",
                     "Inspect exported data files for process_date",
                     "Keys/content reflect kwargs (pipe format, '|' separator, no header) — NOT the spec values."),
            ],
        },
        {
            "id": "TC-003",
            "title": "Happy path — spec fields override built-in defaults",
            "type": "Happy Path",
            "priority": "Medium",
            "objective": "Verify optional spec fields are applied when no kwarg is supplied, overriding defaults.",
            "steps": [
                step("Prepare a contract JSON overriding a default root.",
                     "spec: bad_records_location=\"landing/acquisition/custom_bad\"",
                     "Contract is valid."),
                step("Invoke run_pipeline WITHOUT a bad_records_location kwarg.",
                     "run_pipeline(\"failed-record-export\", minio_config_path=..., process_date=\"20260313\")",
                     "Run completes."),
                step("Inspect where clean-bad rows were written.",
                     "List objects under landing/acquisition/custom_bad/20260313/",
                     "Clean-bad files are written under the spec-provided root, not the default landing/acquisition/bad."),
            ],
        },
        {
            "id": "TC-004",
            "title": "Negative — missing process_date",
            "type": "Negative",
            "priority": "Highest",
            "objective": "The run must fail fast and write nothing when process_date is absent.",
            "steps": [
                step("Invoke run_pipeline without process_date.",
                     "run_pipeline(\"failed-record-export\", minio_config_path=...)  # no process_date",
                     "A clear, actionable error is raised indicating process_date is required."),
                step("Inspect MinIO for any new objects under the run prefixes.",
                     "List bucket prefixes",
                     "No data files, flags or .keep markers are created."),
            ],
        },
        {
            "id": "TC-005",
            "title": "Negative — missing / unresolvable contract path",
            "type": "Negative",
            "priority": "High",
            "objective": "An invalid minio_config_path is rejected with a clear error.",
            "steps": [
                step("Invoke run_pipeline with a non-existent contract path.",
                     "minio_config_path=config/aml/does_not_exist.json; process_date=20260313",
                     "Run fails with an error identifying the missing/unreadable contract object."),
                step("Verify no partial output is produced.",
                     "List bucket prefixes for 20260313",
                     "No objects written."),
            ],
        },
        {
            "id": "TC-006",
            "title": "Negative — unknown pipeline name",
            "type": "Negative",
            "priority": "Medium",
            "objective": "Only the exact registered name is accepted.",
            "steps": [
                step("Invoke run_pipeline with a misspelt name.",
                     "run_pipeline(\"failed_record_export\", ...)  # underscores, wrong",
                     "Runner rejects the unknown pipeline name with a clear error; stage does not execute."),
            ],
        },
        {
            "id": "TC-007",
            "title": "Boundary — process_date format validation",
            "type": "Boundary",
            "priority": "High",
            "objective": "Only well-formed YYYYMMDD dates are accepted; malformed values are rejected.",
            "steps": [
                step("Run with a hyphenated date.",
                     "process_date=2026-03-13",
                     "Rejected as malformed (expected compact YYYYMMDD) OR no tables resolve — documented, deterministic failure, no partial writes."),
                step("Run with a DDMMYYYY value.",
                     "process_date=13032026",
                     "Does not silently succeed against 13-Mar tables; behaves deterministically per the YYYYMMDD contract."),
                step("Run with an impossible calendar date.",
                     "process_date=20261332  (month 13, day 32)",
                     "Rejected / yields no matching quarantine tables; no spurious output."),
                step("Run with empty and null values.",
                     "process_date='' and process_date=None",
                     "Rejected fast with a clear error; nothing written."),
            ],
        },
    ],
})


# ===========================================================================
# DXV-FRE-002 — Quarantine source reading & per-table iteration
# ===========================================================================
STORIES.append({
    "id": "DXV-FRE-002",
    "filename": "DXV-FRE-002_Quarantine-Source-Reading-and-Iteration",
    "title": "Read Iceberg quarantine tables and iterate contract tables safely",
    "epic": "Quarantine Source Acquisition",
    "labels": ["dxv", "failed-record-export", "iceberg", "quarantine", "integration"],
    "priority": "Highest",
    "story_points": 5,
    "components": ["failed-record-export"],
    "persona": "AML data engineer",
    "want": (
        "the exporter to resolve and read the correct Iceberg quarantine table for each "
        "logical table in the contract for the run's process_date"
    ),
    "benefit": (
        "every table that genuinely has validation failures is exported, while tables "
        "with no quarantine data are skipped without failing the whole run"
    ),
    "description": [
        "For each table_name listed in the contract's tables[] array, the exporter reads "
        "the corresponding Iceberg quarantine table. The quarantine table name is derived "
        "as {CATALOG}.{WORKSPACE_ID}.quarantine_{table_name}_{process_date}, where CATALOG "
        "and WORKSPACE_ID come from the environment.",
        "These quarantine rows are exactly the rows that previously failed data-validation "
        "in the upstream stage. The exporter does not re-run validation; it reads what is "
        "already quarantined for that table and date.",
        "Resilience is a core requirement: if a quarantine table for a given contract table "
        "does not exist for that date (for example there were no failed rows, or the "
        "quarantine table was already dropped), that table is skipped. A missing table is "
        "NOT a hard failure for the whole export — other tables continue to be processed.",
    ],
    "context": [
        ("Quarantine table name", "{CATALOG}.{WORKSPACE_ID}.quarantine_{table_name}_{process_date}"),
        ("Source rows", "Rows that already failed data-validation upstream."),
        ("tables[]", "Logical table_name entries in the contract JSON whose quarantine tables are export sources."),
        ("Missing table", "Skipped (not a hard failure) — e.g. no failed rows, or quarantine already dropped."),
    ],
    "acceptance": [
        "For each table_name in tables[], the exporter targets {CATALOG}.{WORKSPACE_ID}.quarantine_{table_name}_{process_date}.",
        "Tables whose quarantine table exists and has rows are exported.",
        "A contract table whose quarantine table is absent for the date is skipped and the run continues.",
        "A run where every contract table is missing completes without a hard failure and produces the acquisition-success outcome (no rows exported).",
        "CATALOG and WORKSPACE_ID are sourced from the environment and used verbatim in the resolved table name.",
    ],
    "test_data": [
        ("CATALOG", "aml_catalog"),
        ("WORKSPACE_ID", "ws_001"),
        ("table_name(s)", "customer, account, transaction"),
        ("process_date", "20260313"),
        ("Resolved name", "aml_catalog.ws_001.quarantine_customer_20260313"),
        ("Contract tables[]", "[\"customer\", \"account\", \"transaction\"]"),
    ],
    "preconditions": [
        "CATALOG and WORKSPACE_ID environment variables are set for the deployment.",
        "The data contract lists the tables under test in tables[].",
    ],
    "tests": [
        {
            "id": "TC-001",
            "title": "Happy path — single table with failures is read & exported",
            "type": "Happy Path",
            "priority": "Highest",
            "objective": "A populated quarantine table is correctly resolved and exported.",
            "steps": [
                step("Seed a quarantine table with failed rows.",
                     "aml_catalog.ws_001.quarantine_customer_20260313 with 25 rows",
                     "Table exists and is populated."),
                step("Set contract tables[] to a single table.",
                     "tables[] = [\"customer\"]",
                     "Contract valid."),
                step("Run the export for process_date 20260313.",
                     "run_pipeline(\"failed-record-export\", ..., process_date=\"20260313\")",
                     "Run completes; the customer quarantine table is read."),
                step("Verify exported objects for customer.",
                     "Inspect bad/aggregated/detailed objects for customer_20260313",
                     "All three data files are produced and contain the 25 rows / their aggregation."),
            ],
        },
        {
            "id": "TC-002",
            "title": "Happy path — multiple tables, mixed content",
            "type": "Happy Path",
            "priority": "High",
            "objective": "Each contract table is resolved independently; populated ones export, the empty/missing one is skipped.",
            "steps": [
                step("Seed two of three quarantine tables.",
                     "customer (10 rows), transaction (4 rows); account quarantine table absent",
                     "Two tables populated, one missing."),
                step("Set contract tables[] to all three.",
                     "tables[] = [\"customer\", \"account\", \"transaction\"]",
                     "Contract valid."),
                step("Run the export.",
                     "process_date=20260313",
                     "Run completes without error."),
                step("Verify outputs per table.",
                     "List objects for each table",
                     "customer and transaction have data files; account has none; the run did not fail because of account."),
            ],
        },
        {
            "id": "TC-003",
            "title": "Negative/Resilience — single missing quarantine table is skipped",
            "type": "Negative",
            "priority": "Highest",
            "objective": "An absent quarantine table for one contract table must not fail the run.",
            "steps": [
                step("Ensure the quarantine table for one contract table does not exist.",
                     "Drop / never create aml_catalog.ws_001.quarantine_account_20260313",
                     "Table is absent for the date."),
                step("Run the export with that table present in tables[].",
                     "tables[] includes \"account\"",
                     "Run completes successfully (no hard failure)."),
                step("Inspect logs / summary for the skipped table.",
                     "Return dict / logs",
                     "account is reported as skipped; other tables processed normally."),
            ],
        },
        {
            "id": "TC-004",
            "title": "Boundary — all contract tables missing",
            "type": "Boundary",
            "priority": "High",
            "objective": "When no quarantine tables exist for any contract table, the run still succeeds with a no-rows outcome.",
            "steps": [
                step("Ensure no quarantine tables exist for the date.",
                     "No quarantine_* tables for 20260313",
                     "All sources absent."),
                step("Run the export.",
                     "tables[] = [\"customer\", \"account\", \"transaction\"]",
                     "Run completes without a hard failure."),
                step("Verify the run is treated as acquisition-success.",
                     "Inspect feedback flag (see DXV-FRE-005)",
                     "No data exports for any table; an acq_success flag is the outcome (no quarantine rows exported)."),
            ],
        },
        {
            "id": "TC-005",
            "title": "Boundary — quarantine table exists but is empty (0 rows)",
            "type": "Boundary",
            "priority": "Medium",
            "objective": "An existing-but-empty quarantine table is handled deterministically.",
            "steps": [
                step("Create an empty quarantine table.",
                     "aml_catalog.ws_001.quarantine_customer_20260313 with 0 rows",
                     "Table exists, no rows."),
                step("Run the export.",
                     "tables[] = [\"customer\"]",
                     "Run completes."),
                step("Inspect outputs and flag.",
                     "Data files + envelope outcome",
                     "Behaviour is deterministic and documented (no failed rows contributes nothing to envelope_error); no crash on empty source."),
            ],
        },
        {
            "id": "TC-006",
            "title": "Negative — environment workspace/catalog mis-set",
            "type": "Negative",
            "priority": "Medium",
            "objective": "Incorrect CATALOG/WORKSPACE_ID resolves to non-existent tables and is handled as skips, not crashes.",
            "steps": [
                step("Set a wrong WORKSPACE_ID.",
                     "WORKSPACE_ID=ws_does_not_exist",
                     "Resolved quarantine names point at non-existent tables."),
                step("Run the export.",
                     "process_date=20260313",
                     "Tables resolve as missing and are skipped; the run does not crash with an unhandled error."),
            ],
        },
    ],
})


# ===========================================================================
# DXV-FRE-003 — Output path resolution, normalisation & ORG_UNIT prefixing
# ===========================================================================
STORIES.append({
    "id": "DXV-FRE-003",
    "filename": "DXV-FRE-003_Path-Resolution-Normalisation-and-ORG_UNIT",
    "title": "Resolve, normalise and prefix output object paths correctly",
    "epic": "Output Layout & Object Keys",
    "labels": ["dxv", "failed-record-export", "minio", "paths", "org-unit", "integration"],
    "priority": "High",
    "story_points": 5,
    "components": ["failed-record-export"],
    "persona": "platform integration engineer",
    "want": (
        "the exporter to place every object under predictable, normalised roots and to "
        "prepend the ORG_UNIT segment when configured"
    ),
    "benefit": (
        "downstream DXV / SFTP tooling can reliably watch and pick up files using stable, "
        "lowercase, slash-clean keys that match typical DXV / NROD layouts"
    ),
    "description": [
        "Output objects are written under three configurable roots: bad_records_location "
        "(clean rows for resubmit), feedback_location (flags/triggers) and report_location "
        "(aggregated + detailed reports). The built-in defaults are landing/acquisition/bad, "
        "landing/acquisition/feedback and landing/acquisition/feedback/reporting respectively.",
        "Configured roots are normalised before use: leading/trailing slashes are stripped "
        "and the value is lowercased, so behaviour matches typical DXV / NROD SFTP layouts. "
        "Full object keys are under the bucket.",
        "If the ORG_UNIT environment variable is set, the exporter prepends {ORG_UNIT}/ to "
        "the path before the configured roots. If ORG_UNIT is unset, the roots sit directly "
        "under the bucket. Object name patterns embed process_date and table_name "
        "(for example {bad_records_location}/{process_date}/{table_name}_{process_date}.{ext}).",
    ],
    "context": [
        ("Default bad root", "landing/acquisition/bad"),
        ("Default feedback root", "landing/acquisition/feedback"),
        ("Default report root", "landing/acquisition/feedback/reporting"),
        ("Normalisation", "Strip leading/trailing slashes and lowercase the configured roots."),
        ("ORG_UNIT prefix", "When set, {ORG_UNIT}/ is prepended BEFORE the configured roots."),
        ("Clean bad pattern", "{bad_records_location}/{process_date}/{table_name}_{process_date}.{ext}"),
        ("Aggregated pattern", "{report_location}/{process_date}/aggregated_{table_name}_{process_date}.{ext}"),
        ("Detailed pattern", "{report_location}/{process_date}/detailed_{table_name}_{process_date}.{ext}"),
    ],
    "acceptance": [
        "With no overrides and ORG_UNIT unset, objects land under the three documented default roots directly beneath the bucket.",
        "A configured root with surrounding slashes and mixed case is normalised (slashes stripped, lowercased) before keys are built.",
        "When ORG_UNIT is set, every object key is prefixed with {ORG_UNIT}/ ahead of the configured root.",
        "Object names exactly follow the documented patterns, embedding process_date and table_name with the correct {ext}.",
        "Overriding one root does not move objects belonging to the other roots.",
    ],
    "test_data": [
        ("ORG_UNIT (set)", "OrgA  ->  prefix 'orga/' after normalisation considerations"),
        ("Un-normalised root", "'/Landing/Acquisition/Bad/'  ->  'landing/acquisition/bad'"),
        ("process_date", "20260313"),
        ("table_name", "customer"),
        ("ext", "csv (from file_format)"),
        ("Expected clean-bad key", "landing/acquisition/bad/20260313/customer_20260313.csv"),
        ("Expected aggregated key", "landing/acquisition/feedback/reporting/20260313/aggregated_customer_20260313.csv"),
    ],
    "preconditions": [
        "A populated quarantine table exists for the table/date under test.",
        "ORG_UNIT is explicitly set or unset per the individual test case.",
    ],
    "tests": [
        {
            "id": "TC-001",
            "title": "Happy path — default roots, ORG_UNIT unset",
            "type": "Happy Path",
            "priority": "High",
            "objective": "All objects land under the documented default roots with correct names.",
            "preconditions": ["ORG_UNIT is unset / empty."],
            "steps": [
                step("Run the export with no path kwargs and no spec overrides.",
                     "process_date=20260313; file_format=csv; table=customer",
                     "Run completes."),
                step("Verify the clean-bad key.",
                     "Expect landing/acquisition/bad/20260313/customer_20260313.csv",
                     "Object exists at exactly that key."),
                step("Verify the aggregated and detailed keys.",
                     "Expect .../feedback/reporting/20260313/aggregated_customer_20260313.csv and detailed_...",
                     "Both objects exist at the documented report paths."),
                step("Verify the feedback flag key.",
                     "Expect landing/acquisition/feedback/20260313/<flag>",
                     "Flag object exists under the feedback root."),
            ],
        },
        {
            "id": "TC-002",
            "title": "Happy path — ORG_UNIT prefix applied",
            "type": "Happy Path",
            "priority": "High",
            "objective": "Setting ORG_UNIT prepends {ORG_UNIT}/ before the configured roots for every object.",
            "preconditions": ["ORG_UNIT=OrgA"],
            "steps": [
                step("Set ORG_UNIT and run the export with default roots.",
                     "ORG_UNIT=OrgA; process_date=20260313; table=customer",
                     "Run completes."),
                step("Verify keys are prefixed.",
                     "Expect <orgunit-prefix>/landing/acquisition/bad/20260313/customer_20260313.csv",
                     "Every object key begins with the ORG_UNIT segment ahead of the configured root."),
                step("Confirm prefix is applied consistently to all three roots + flags.",
                     "Inspect bad, report and feedback keys",
                     "All carry the same ORG_UNIT prefix."),
            ],
        },
        {
            "id": "TC-003",
            "title": "Boundary/Normalisation — un-normalised configured roots",
            "type": "Boundary",
            "priority": "High",
            "objective": "Roots with surrounding slashes and uppercase are normalised before keys are built.",
            "steps": [
                step("Override roots with messy values.",
                     "bad_records_location='/Landing/Acquisition/Bad/'",
                     "Accepted by config."),
                step("Run the export.",
                     "process_date=20260313; table=customer",
                     "Run completes."),
                step("Verify the resulting key is normalised.",
                     "Expect landing/acquisition/bad/20260313/customer_20260313.csv",
                     "Leading/trailing slashes stripped and value lowercased; no doubled '//' or mixed case in the key."),
            ],
        },
        {
            "id": "TC-004",
            "title": "Happy path — selective root override isolation",
            "type": "Happy Path",
            "priority": "Medium",
            "objective": "Overriding one root does not relocate objects for the other roots.",
            "steps": [
                step("Override only the report root.",
                     "report_location='landing/acquisition/custom_reporting'",
                     "Config accepted."),
                step("Run the export.",
                     "process_date=20260313; table=customer",
                     "Run completes."),
                step("Verify report objects moved but bad/feedback did not.",
                     "Inspect all three roots",
                     "aggregated/detailed under custom_reporting; clean-bad still under landing/acquisition/bad; flag still under landing/acquisition/feedback."),
            ],
        },
        {
            "id": "TC-005",
            "title": "Negative — overlapping/empty root values",
            "type": "Negative",
            "priority": "Low",
            "objective": "Empty or degenerate root overrides are handled predictably (no keys with leading slash or empty segment).",
            "steps": [
                step("Override a root with an empty string.",
                     "bad_records_location=''",
                     "Config accepted or rejected — behaviour is documented and deterministic."),
                step("Run the export and inspect keys.",
                     "process_date=20260313; table=customer",
                     "No object key is produced with a leading '/' or an empty path segment (e.g. never '//20260313/...')."),
            ],
        },
    ],
})


# ===========================================================================
# DXV-FRE-004 — Data file generation (clean bad / aggregated / detailed)
# ===========================================================================
STORIES.append({
    "id": "DXV-FRE-004",
    "filename": "DXV-FRE-004_Data-File-Generation-Bad-Aggregated-Detailed",
    "title": "Generate clean-bad, aggregated and detailed export files correctly",
    "epic": "Data Export Content",
    "labels": ["dxv", "failed-record-export", "exports", "aggregation", "integration"],
    "priority": "Highest",
    "story_points": 8,
    "components": ["failed-record-export"],
    "persona": "AML data analyst",
    "want": (
        "the exporter to produce three distinct files per table — a clean resubmit copy, "
        "an aggregated error summary, and a full detailed export"
    ),
    "benefit": (
        "I can resubmit corrected records, triage error patterns quickly, and still retain "
        "the full per-row validation detail for investigation"
    ),
    "description": [
        "For each exported table the stage writes three data files using one shared writer "
        "contract (delimiter + header from the spec). The Clean bad file contains the same "
        "rows as quarantine but with the validation_errors and validation_timestamp columns "
        "dropped, so the file is a clean copy suitable for resubmission.",
        "The Aggregated file contains counts per (error_type, field_name) after exploding the "
        "validation_errors array. Importantly, if every row has an empty or null errors array, "
        "the exporter writes one fallback summary row — (validation_error, empty field, total "
        "row count) — so the file is never header-only. This fallback aligns with the envelope "
        "flag behaviour when errors cannot be exploded.",
        "The Detailed file is the full row set with validation_errors retained as JSON on each "
        "row. Object names follow the documented patterns: {table}_{date}, aggregated_{table}_"
        "{date} and detailed_{table}_{date}, each with the configured extension.",
    ],
    "context": [
        ("Clean bad", "Quarantine rows with validation_errors and validation_timestamp dropped."),
        ("Aggregated", "Counts per (error_type, field_name) after exploding validation_errors."),
        ("Aggregated fallback", "If all errors arrays empty/null -> one row: validation_error, empty field, total row count."),
        ("Detailed", "Full row set with validation_errors as JSON on each row."),
        ("Writer contract", "Delimiter + header come from the merged spec (see DXV-FRE-006)."),
    ],
    "acceptance": [
        "Clean-bad output contains all quarantine rows but excludes the validation_errors and validation_timestamp columns.",
        "Aggregated output contains one row per distinct (error_type, field_name) with a correct count, derived by exploding validation_errors.",
        "When all rows have empty/null validation_errors, the aggregated file contains exactly one fallback row: (validation_error, empty field, total row count) — never header-only.",
        "Detailed output contains every quarantine row with validation_errors preserved as JSON.",
        "All three files are written at the documented object keys with the configured extension and delimiter/header.",
    ],
    "test_data": [
        ("Quarantine row", "customer_id, name, ..., validation_errors (array), validation_timestamp"),
        ("validation_errors element", "{\"error_type\":\"null_check\",\"field_name\":\"customer_id\"}"),
        ("Multi-error row", "[{null_check, customer_id}, {format, dob}]"),
        ("Empty errors row", "validation_errors = [] or null"),
        ("Aggregated row", "error_type, field_name, count  ->  null_check, customer_id, 12"),
        ("Fallback aggregated row", "validation_error, <empty>, <total row count>"),
    ],
    "preconditions": [
        "A quarantine table for the table/date under test exists and is populated as the case requires.",
        "Spec delimiter/header are known so output content can be parsed and asserted.",
    ],
    "tests": [
        {
            "id": "TC-001",
            "title": "Happy path — clean-bad drops validation columns",
            "type": "Happy Path",
            "priority": "Highest",
            "objective": "Clean-bad file is a faithful copy minus validation_errors and validation_timestamp.",
            "steps": [
                step("Seed quarantine rows including validation columns.",
                     "10 rows, each with business columns + validation_errors + validation_timestamp",
                     "Table populated."),
                step("Run the export.",
                     "table=customer; process_date=20260313; file_format=csv; include_header=true",
                     "Run completes; clean-bad object written."),
                step("Open the clean-bad file and inspect the header.",
                     "landing/acquisition/bad/20260313/customer_20260313.csv",
                     "Header contains business columns only; validation_errors and validation_timestamp are absent."),
                step("Count and spot-check rows.",
                     "Compare to source",
                     "Row count equals source (10); business values are unchanged."),
            ],
        },
        {
            "id": "TC-002",
            "title": "Happy path — aggregated counts per (error_type, field_name)",
            "type": "Happy Path",
            "priority": "Highest",
            "objective": "Aggregation explodes validation_errors and counts each (error_type, field_name) pair.",
            "steps": [
                step("Seed rows with known, countable errors.",
                     "12 rows null_check/customer_id; 5 rows format/dob; 3 rows range/score",
                     "Quarantine populated with a known error distribution."),
                step("Run the export.",
                     "table=customer; process_date=20260313",
                     "Aggregated object written."),
                step("Open the aggregated file and verify the rows.",
                     ".../reporting/20260313/aggregated_customer_20260313.csv",
                     "Rows: (null_check, customer_id, 12), (format, dob, 5), (range, score, 3); counts exactly match."),
            ],
        },
        {
            "id": "TC-003",
            "title": "Boundary — multi-error rows explode correctly",
            "type": "Boundary",
            "priority": "High",
            "objective": "A single row carrying multiple errors increments each relevant (error_type, field_name).",
            "steps": [
                step("Seed rows where one row has two errors.",
                     "Row A: [{null_check,customer_id},{format,dob}]; 4 more rows: [{null_check,customer_id}]",
                     "Quarantine populated."),
                step("Run the export.",
                     "table=customer; process_date=20260313",
                     "Aggregated object written."),
                step("Verify the counts reflect exploded errors.",
                     "Inspect aggregated rows",
                     "(null_check, customer_id) = 5 and (format, dob) = 1 — the multi-error row contributes to both."),
            ],
        },
        {
            "id": "TC-004",
            "title": "Boundary — all-empty errors triggers single fallback row",
            "type": "Boundary",
            "priority": "Highest",
            "objective": "When validation_errors cannot be exploded, the aggregated file holds exactly one fallback summary row.",
            "steps": [
                step("Seed rows all with empty/null errors.",
                     "8 rows, every validation_errors = [] or null",
                     "Quarantine populated; nothing to explode."),
                step("Run the export.",
                     "table=customer; process_date=20260313",
                     "Aggregated object written."),
                step("Open the aggregated file.",
                     "Inspect rows",
                     "Exactly ONE data row: (validation_error, <empty field>, 8) — the total row count; file is NOT header-only."),
                step("Cross-check the envelope flag outcome.",
                     "See DXV-FRE-005",
                     "Fallback aligns with envelope_error single fallback line for that table."),
            ],
        },
        {
            "id": "TC-005",
            "title": "Happy path — detailed retains validation_errors as JSON",
            "type": "Happy Path",
            "priority": "High",
            "objective": "Detailed file keeps the full row set with validation_errors serialised as JSON.",
            "steps": [
                step("Seed rows with structured errors.",
                     "6 rows with non-empty validation_errors arrays",
                     "Quarantine populated."),
                step("Run the export.",
                     "table=customer; process_date=20260313",
                     "Detailed object written."),
                step("Open the detailed file and inspect a row's validation_errors cell.",
                     ".../reporting/20260313/detailed_customer_20260313.csv",
                     "Cell contains valid JSON (e.g. [{\"error_type\":\"null_check\",\"field_name\":\"customer_id\"}]); all 6 rows present."),
                step("Confirm delimiter does not corrupt embedded JSON.",
                     "Parse the file with the configured delimiter",
                     "JSON commas do not break columns (proper quoting/escaping applied)."),
            ],
        },
        {
            "id": "TC-006",
            "title": "Negative — malformed validation_errors payload",
            "type": "Negative",
            "priority": "Medium",
            "objective": "A row with a malformed errors payload is handled without aborting the whole export.",
            "steps": [
                step("Seed a row with a non-array / malformed errors value.",
                     "validation_errors = '{not-json' on one row, valid on others",
                     "Quarantine populated with one bad payload."),
                step("Run the export.",
                     "table=customer; process_date=20260313",
                     "Run completes; the export does not crash on the single malformed payload."),
                step("Inspect aggregated/detailed handling of the bad row.",
                     "Review outputs / logs",
                     "Bad payload is handled deterministically (e.g. counted under fallback / surfaced), other rows unaffected."),
            ],
        },
    ],
})


# ===========================================================================
# DXV-FRE-005 — Envelope flag-file generation & semantics
# ===========================================================================
STORIES.append({
    "id": "DXV-FRE-005",
    "filename": "DXV-FRE-005_Envelope-Flag-File-Generation-and-Semantics",
    "title": "Emit the correct acquisition success / error envelope flag per run",
    "epic": "Feedback Flags & Envelope Semantics",
    "labels": ["dxv", "failed-record-export", "flags", "envelope", "integration"],
    "priority": "Highest",
    "story_points": 5,
    "components": ["failed-record-export"],
    "persona": "file-based automation owner",
    "want": (
        "exactly one envelope flag file per run that states whether the acquisition "
        "succeeded cleanly or had validation failures"
    ),
    "benefit": (
        "downstream DXV file-based automation can trigger the correct branch (success vs "
        "error handling) from a single, predictable trigger file"
    ),
    "description": [
        "Every run produces exactly one envelope flag. When NO quarantine rows were exported "
        "(i.e. no table had failures), the stage writes acq_success_{YYYYMMDD}.zip.flag. When "
        "ANY table had failures, it instead writes envelope_error_{YYYYMMDD}.zip.flag. The two "
        "are mutually exclusive — one flag per run — using DXV-compatible naming.",
        "The envelope_error flag body is text, with one failure summary per line in the form: "
        "{table_name}_{DDMMYYYY}, {reason}, {count}. The first column is the logical table name "
        "plus the processing date in DDMMYYYY (e.g. customer_13032026 for 13 March 2026). The "
        "reason comes from the validation result (error_type and field_name, space-separated). "
        "If validation_errors cannot be exploded for a table, a single fallback line uses the "
        "row count instead.",
        "The acq_success flag body is a single newline, kept that way for DXV-style trigger "
        "compatibility. The exact payload should be treated as part of the integration contract "
        "with downstream pickup. Both flags are written under the feedback root for the date.",
    ],
    "context": [
        ("acq_success flag", "acq_success_{YYYYMMDD}.zip.flag — written when NO quarantine rows exported."),
        ("envelope_error flag", "envelope_error_{YYYYMMDD}.zip.flag — written when ANY table had failures."),
        ("One per run", "The two flags are mutually exclusive; exactly one is emitted."),
        ("error line format", "{table_name}_{DDMMYYYY}, {reason}, {count}"),
        ("Date in line", "DDMMYYYY (e.g. customer_13032026), distinct from the YYYYMMDD in the filename."),
        ("Reason", "error_type and field_name, space-separated; fallback line uses count when errors cannot be exploded."),
        ("acq_success body", "A single newline (exact payload is part of the integration contract)."),
    ],
    "acceptance": [
        "A run with zero exported quarantine rows writes acq_success_{YYYYMMDD}.zip.flag and no envelope_error flag.",
        "A run where at least one table had failures writes envelope_error_{YYYYMMDD}.zip.flag and no acq_success flag.",
        "Never are both flags present for the same run.",
        "Each envelope_error line is '{table_name}_{DDMMYYYY}, {reason}, {count}' with the date in DDMMYYYY.",
        "A table whose errors cannot be exploded contributes a single fallback line using the row count.",
        "The acq_success flag body is exactly a single newline.",
        "Flag filename uses YYYYMMDD while the in-body first column uses DDMMYYYY.",
    ],
    "test_data": [
        ("process_date", "20260313  (filename uses 20260313)"),
        ("In-body date", "13032026  (DDMMYYYY for 13 March 2026)"),
        ("Success flag name", "acq_success_20260313.zip.flag"),
        ("Error flag name", "envelope_error_20260313.zip.flag"),
        ("Error line example", "customer_13032026, null_check customer_id, 12"),
        ("Fallback line example", "account_13032026, 7"),
    ],
    "preconditions": [
        "Quarantine sources are seeded to match the success/error scenario under test.",
        "The feedback root key prefix for the date is known so the flag can be located.",
    ],
    "tests": [
        {
            "id": "TC-001",
            "title": "Happy path — acq_success when no failures",
            "type": "Happy Path",
            "priority": "Highest",
            "objective": "A clean run writes only the acquisition-success flag.",
            "steps": [
                step("Ensure no quarantine rows will be exported.",
                     "No quarantine tables / all empty for 20260313",
                     "No failures present."),
                step("Run the export.",
                     "process_date=20260313",
                     "Run completes."),
                step("Locate the flag under the feedback root.",
                     "landing/acquisition/feedback/20260313/",
                     "acq_success_20260313.zip.flag exists; envelope_error_20260313.zip.flag does NOT."),
                step("Inspect the success flag body.",
                     "Read object bytes",
                     "Body is exactly a single newline character."),
            ],
        },
        {
            "id": "TC-002",
            "title": "Happy path — envelope_error when failures exist",
            "type": "Happy Path",
            "priority": "Highest",
            "objective": "A run with failures writes only the envelope-error flag with correct line format.",
            "steps": [
                step("Seed a table with explodable errors.",
                     "customer: 12 rows null_check/customer_id",
                     "Quarantine populated."),
                step("Run the export.",
                     "process_date=20260313",
                     "Run completes."),
                step("Locate the flag.",
                     "landing/acquisition/feedback/20260313/",
                     "envelope_error_20260313.zip.flag exists; acq_success does NOT."),
                step("Inspect the error line.",
                     "Read object text",
                     "Line: 'customer_13032026, null_check customer_id, 12' (DDMMYYYY date; reason space-separated; correct count)."),
            ],
        },
        {
            "id": "TC-003",
            "title": "Boundary — multiple tables produce multiple lines",
            "type": "Boundary",
            "priority": "High",
            "objective": "Each failing table contributes its own summary line(s) to one envelope_error flag.",
            "steps": [
                step("Seed multiple failing tables.",
                     "customer (12 null_check/customer_id), transaction (4 range/amount)",
                     "Two tables populated."),
                step("Run the export.",
                     "process_date=20260313",
                     "Run completes."),
                step("Inspect the flag body lines.",
                     "Read object text",
                     "Contains 'customer_13032026, null_check customer_id, 12' and 'transaction_13032026, range amount, 4'."),
            ],
        },
        {
            "id": "TC-004",
            "title": "Boundary — fallback line when errors cannot be exploded",
            "type": "Boundary",
            "priority": "High",
            "objective": "A table with empty/null errors contributes a single fallback line using the row count.",
            "steps": [
                step("Seed a failing table whose errors are all empty/null.",
                     "account: 7 rows, validation_errors = [] / null",
                     "Quarantine populated; not explodable."),
                step("Run the export.",
                     "process_date=20260313",
                     "Run completes; this counts as a failure for envelope purposes."),
                step("Inspect the fallback line.",
                     "Read object text",
                     "Single fallback line for account uses the row count, e.g. 'account_13032026, 7' (count instead of reason)."),
            ],
        },
        {
            "id": "TC-005",
            "title": "Negative — never both flags for one run",
            "type": "Negative",
            "priority": "Highest",
            "objective": "The two flags are mutually exclusive in all scenarios.",
            "steps": [
                step("Run a mixed scenario (some failures, some clean tables).",
                     "customer has failures; account is clean/missing",
                     "Run completes."),
                step("Enumerate flag objects for the date.",
                     "List landing/acquisition/feedback/20260313/*.flag",
                     "Exactly one flag present (envelope_error, because at least one table failed); acq_success absent."),
            ],
        },
        {
            "id": "TC-006",
            "title": "Boundary — date encoding split (filename vs body)",
            "type": "Boundary",
            "priority": "Medium",
            "objective": "Filename uses YYYYMMDD while the in-body first column uses DDMMYYYY.",
            "steps": [
                step("Run with a date whose digit pattern makes the two formats obviously different.",
                     "process_date=20260901 (1 Sep 2026 -> body 01092026)",
                     "Run completes with failures present."),
                step("Compare filename and body date encodings.",
                     "Filename vs first column",
                     "Filename: envelope_error_20260901.zip.flag; body column: <table>_01092026 — encodings differ as documented."),
            ],
        },
    ],
})


# ===========================================================================
# DXV-FRE-006 — Export format, delimiter & header handling
# ===========================================================================
STORIES.append({
    "id": "DXV-FRE-006",
    "filename": "DXV-FRE-006_Export-Format-Delimiter-and-Header-Handling",
    "title": "Apply export file_format, separator and header rules correctly",
    "epic": "Writer Format & Delimiters",
    "labels": ["dxv", "failed-record-export", "format", "delimiter", "header", "integration"],
    "priority": "High",
    "story_points": 5,
    "components": ["failed-record-export"],
    "persona": "downstream integration engineer",
    "want": (
        "control over the export file extension, delimiter and header, including reusing the "
        "ingest settings or overriding them with export-only values"
    ),
    "benefit": (
        "exported keys and content match what downstream pickup expects, even when export "
        "formatting must differ from the ingest formatting"
    ),
    "description": [
        "The three data exports share one writer contract: a delimiter (separator) and a header "
        "flag from the merged spec. The contract's input.extension and input.delimiter seed the "
        "export file_format and separator unless top-level overrides are set. Supported export "
        "extensions for object names are csv and txt; {ext} follows file_format.",
        "Two export-only file_format values exist for when export keys must differ from ingest: "
        "pipe and gs. These fix the separator in the writer. For example, with ingest "
        "input={extension:csv, delimiter:'|'} and export file_format=pipe, keys use .pipe. To get "
        ".csv keys with pipe-separated content instead, set file_format=csv and separator='|'.",
        "txt export defaults to a tab separator if none is set. include_header is a boolean that "
        "defaults to true. All of file_format, separator and include_header may be set at the "
        "top level of the contract JSON and/or via the matching run_pipeline kwargs.",
    ],
    "context": [
        ("Seeding", "input.extension / input.delimiter seed export file_format / separator unless overridden."),
        ("Ingest extensions", "Ingest allows input.extension csv / txt only on MinIO object names."),
        ("Export-only formats", "pipe and gs fix the separator in the writer; used when export keys differ from ingest."),
        (".csv with pipe content", "Use file_format=csv and separator='|' (keys end .csv, content pipe-separated)."),
        ("txt default separator", "Tab, if no separator is set."),
        ("include_header", "Boolean, default true."),
    ],
    "acceptance": [
        "With no overrides, export file_format and separator are seeded from input.extension and input.delimiter.",
        "A top-level file_format / separator / include_header overrides the seeded value.",
        "file_format=pipe and file_format=gs fix the writer separator and produce .pipe / .gs object keys respectively.",
        "file_format=csv with separator='|' produces .csv keys whose content is pipe-separated.",
        "txt export with no separator uses a tab delimiter.",
        "include_header=true emits a header row; include_header=false omits it.",
    ],
    "test_data": [
        ("input.extension / delimiter", "csv / ',' (seeds export csv + comma)"),
        ("file_format=txt", "no separator -> tab-delimited, .txt keys"),
        ("file_format=pipe", "keys end .pipe; separator fixed by writer"),
        ("file_format=gs", "keys end .gs; separator fixed by writer"),
        ("csv + separator '|'", ".csv keys, pipe-separated content"),
        ("include_header", "true (default) | false"),
    ],
    "preconditions": [
        "A populated quarantine table exists for the table/date under test.",
        "Contract input.extension/input.delimiter are set to known seed values.",
    ],
    "tests": [
        {
            "id": "TC-001",
            "title": "Happy path — seed from ingest (csv, comma)",
            "type": "Happy Path",
            "priority": "High",
            "objective": "With no overrides, export inherits csv extension and comma separator from ingest.",
            "steps": [
                step("Set contract ingest settings; no export overrides.",
                     "input={extension:'csv', delimiter:','}",
                     "Contract valid."),
                step("Run the export.",
                     "process_date=20260313; table=customer",
                     "Run completes."),
                step("Inspect object key extension and content delimiter.",
                     "customer_20260313.csv",
                     "Key ends .csv; rows are comma-separated; header present by default."),
            ],
        },
        {
            "id": "TC-002",
            "title": "Happy path — txt defaults to tab",
            "type": "Happy Path",
            "priority": "High",
            "objective": "file_format=txt with no separator yields tab-delimited content.",
            "steps": [
                step("Set file_format=txt with no separator.",
                     "file_format='txt'  (separator unset)",
                     "Config accepted."),
                step("Run the export.",
                     "process_date=20260313; table=customer",
                     "Run completes."),
                step("Inspect key and delimiter.",
                     "customer_20260313.txt",
                     "Key ends .txt; fields are separated by a TAB character."),
            ],
        },
        {
            "id": "TC-003",
            "title": "Happy path — export-only pipe format (.pipe keys)",
            "type": "Happy Path",
            "priority": "High",
            "objective": "file_format=pipe fixes the separator and emits .pipe object keys.",
            "steps": [
                step("Configure ingest csv but export pipe.",
                     "input={extension:'csv', delimiter:'|'}; file_format='pipe'",
                     "Config accepted."),
                step("Run the export.",
                     "process_date=20260313; table=customer",
                     "Run completes."),
                step("Inspect key extension and content separator.",
                     "customer_20260313.pipe",
                     "Key ends .pipe; content separator is fixed by the writer for pipe."),
            ],
        },
        {
            "id": "TC-004",
            "title": "Happy path — csv keys with pipe content",
            "type": "Happy Path",
            "priority": "Medium",
            "objective": "file_format=csv + separator='|' yields .csv keys whose content is pipe-separated.",
            "steps": [
                step("Set file_format=csv and separator='|'.",
                     "file_format='csv'; separator='|'",
                     "Config accepted."),
                step("Run the export.",
                     "process_date=20260313; table=customer",
                     "Run completes."),
                step("Inspect key and content.",
                     "customer_20260313.csv",
                     "Key ends .csv but fields are separated by '|'."),
            ],
        },
        {
            "id": "TC-005",
            "title": "Happy path — gs export-only format (.gs keys)",
            "type": "Happy Path",
            "priority": "Low",
            "objective": "file_format=gs fixes the writer separator and emits .gs keys.",
            "steps": [
                step("Set file_format=gs.",
                     "file_format='gs'",
                     "Config accepted."),
                step("Run the export and inspect.",
                     "process_date=20260313; table=customer",
                     "Key ends .gs; writer separator is fixed for gs."),
            ],
        },
        {
            "id": "TC-006",
            "title": "Happy path — include_header toggles header row",
            "type": "Happy Path",
            "priority": "High",
            "objective": "Header row appears when true (default) and is omitted when false.",
            "steps": [
                step("Run with include_header=true (default).",
                     "include_header unset OR true",
                     "Output has a header row as the first line."),
                step("Run with include_header=false.",
                     "include_header=false",
                     "Output has NO header row; first line is data."),
            ],
        },
        {
            "id": "TC-007",
            "title": "Negative — unsupported file_format value",
            "type": "Negative",
            "priority": "Medium",
            "objective": "An unsupported file_format is rejected rather than silently producing an odd key.",
            "steps": [
                step("Set an unsupported export format.",
                     "file_format='parquet'",
                     "Config is rejected with a clear error (supported: csv, txt, pipe, gs)."),
                step("Confirm no malformed objects are written.",
                     "List objects for 20260313",
                     "No object with an unexpected extension is created."),
            ],
        },
        {
            "id": "TC-008",
            "title": "Boundary — delimiter collides with data content",
            "type": "Boundary",
            "priority": "Medium",
            "objective": "When the chosen delimiter appears inside field values, content remains parseable.",
            "steps": [
                step("Seed values containing the delimiter.",
                     "Comma-delimited export; a name field value = 'Smith, John'",
                     "Quarantine populated with delimiter-bearing values."),
                step("Run the export.",
                     "file_format=csv; separator=','; table=customer",
                     "Run completes."),
                step("Parse the output with the configured delimiter.",
                     "Re-parse file",
                     "Field 'Smith, John' stays a single field (proper quoting/escaping); column count per row is stable."),
            ],
        },
    ],
})


# ===========================================================================
# DXV-FRE-007 — RFFilespec headerless alignment
# ===========================================================================
STORIES.append({
    "id": "DXV-FRE-007",
    "filename": "DXV-FRE-007_RFFilespec-Headerless-Alignment",
    "title": "Align headerless export shape with RFFilespec ingest",
    "epic": "RFFilespec / Headerless Compatibility",
    "labels": ["dxv", "failed-record-export", "rffilespec", "headerless", "integration"],
    "priority": "Medium",
    "story_points": 3,
    "components": ["failed-record-export"],
    "persona": "AML data engineer",
    "want": (
        "headerless bad-row and report files when ingest uses RFFilespec/XML-driven, "
        "headerless column ordering"
    ),
    "benefit": (
        "the resubmit and report files match the exact shape the ingest expects, avoiding a "
        "header line that RFFilespec ingest would not tolerate"
    ),
    "description": [
        "When the contract sets input.use_rffilespec to true, ingest uses headerless, "
        "RFFilespec/XML-driven column ordering. Failed-record export, however, still defaults "
        "include_header to true regardless of use_rffilespec.",
        "Therefore, to produce headerless bad rows and reports that match the RFFilespec ingest "
        "shape, the team must explicitly set include_header to false — either in the contract "
        "JSON or by passing include_header=False to run_pipeline.",
        "Export path roots remain global for this stage (bad_records_location, feedback_location, "
        "report_location). There is no separate per-table export path layout introduced by "
        "RFFilespec; only the header behaviour needs aligning.",
    ],
    "context": [
        ("input.use_rffilespec", "When true, ingest is headerless with XML-driven column order."),
        ("Export default", "include_header still defaults to true even when use_rffilespec is true."),
        ("Required action", "Set include_header=false (contract) or include_header=False (kwarg) for headerless export."),
        ("Path roots", "Remain global (bad/feedback/report); no per-table export path layout."),
    ],
    "acceptance": [
        "With use_rffilespec=true and no header override, export still emits a header row (documented default).",
        "With use_rffilespec=true and include_header=false (contract or kwarg), bad rows and reports are headerless.",
        "Headerless output column order is consistent with the RFFilespec/XML-driven ingest order.",
        "Export path roots remain the global bad/feedback/report roots regardless of use_rffilespec.",
    ],
    "test_data": [
        ("input.use_rffilespec", "true"),
        ("include_header (kwarg)", "False"),
        ("include_header (contract)", "false"),
        ("table_name", "customer"),
        ("process_date", "20260313"),
    ],
    "preconditions": [
        "A contract configured with input.use_rffilespec=true and a corresponding RFFilespec/XML column order.",
        "A populated quarantine table for the table/date under test.",
    ],
    "tests": [
        {
            "id": "TC-001",
            "title": "Negative/Default — rffilespec true but header not overridden",
            "type": "Negative",
            "priority": "High",
            "objective": "Confirm export still emits a header by default even with use_rffilespec=true (documents the gotcha).",
            "steps": [
                step("Configure contract with use_rffilespec=true and no header override.",
                     "input.use_rffilespec=true; include_header unset",
                     "Contract valid."),
                step("Run the export.",
                     "process_date=20260313; table=customer",
                     "Run completes."),
                step("Inspect the clean-bad file's first line.",
                     "Open customer_20260313 export",
                     "A header row IS present (export default true) — i.e. it does NOT auto-match headerless ingest."),
            ],
        },
        {
            "id": "TC-002",
            "title": "Happy path — headerless via kwarg",
            "type": "Happy Path",
            "priority": "High",
            "objective": "include_header=False kwarg produces headerless bad rows and reports.",
            "steps": [
                step("Run with use_rffilespec=true and include_header=False kwarg.",
                     "run_pipeline(..., include_header=False, process_date=\"20260313\")",
                     "Run completes."),
                step("Inspect bad, aggregated and detailed files.",
                     "Open all three exports for customer",
                     "None of the files contain a header row; the first line is data."),
                step("Verify column order matches RFFilespec/XML order.",
                     "Compare to the ingest column order",
                     "Headerless columns are positioned to match the RFFilespec-driven ingest shape."),
            ],
        },
        {
            "id": "TC-003",
            "title": "Happy path — headerless via contract field",
            "type": "Happy Path",
            "priority": "Medium",
            "objective": "include_header=false in the contract JSON also yields headerless output.",
            "steps": [
                step("Set include_header=false in the contract; no kwarg.",
                     "contract: include_header=false; use_rffilespec=true",
                     "Contract valid."),
                step("Run the export.",
                     "process_date=20260313; table=customer",
                     "Run completes."),
                step("Inspect output header behaviour.",
                     "Open exports",
                     "Files are headerless, matching the contract setting."),
            ],
        },
        {
            "id": "TC-004",
            "title": "Happy path — global roots unaffected by rffilespec",
            "type": "Happy Path",
            "priority": "Low",
            "objective": "Export path roots remain the global bad/feedback/report roots under RFFilespec.",
            "steps": [
                step("Run a headerless RFFilespec export.",
                     "use_rffilespec=true; include_header=False; process_date=20260313",
                     "Run completes."),
                step("Inspect object keys.",
                     "List keys for the date",
                     "Objects are under the same global bad/feedback/report roots; no per-table export path layout appears."),
            ],
        },
    ],
})


# ===========================================================================
# DXV-FRE-008 — Storage behaviour, .keep markers & *.zip.flag naming
# ===========================================================================
STORIES.append({
    "id": "DXV-FRE-008",
    "filename": "DXV-FRE-008_Storage-Behaviour-Keep-Markers-and-Zip-Flag-Naming",
    "title": "Write .keep prefix markers and apply *.zip.flag naming conventions",
    "epic": "Object-Store Behaviour & Naming",
    "labels": ["dxv", "failed-record-export", "minio", "keep-markers", "naming", "integration"],
    "priority": "High",
    "story_points": 5,
    "components": ["failed-record-export"],
    "persona": "platform integration engineer",
    "want": (
        "every run to create the three date-prefix .keep markers and to name flag objects with "
        "the DXV-compatible *.zip.flag convention"
    ),
    "benefit": (
        "downstream object-store tooling always finds a concrete prefix key to watch, and "
        "outbound PGP/zip routing treats the flags correctly as non-zip objects"
    ),
    "description": [
        "Before any per-table exports, every run writes three zero-byte .keep objects — one under "
        "{bad_records_location}/{process_date}/, one under {report_location}/{process_date}/ and "
        "one under {feedback_location}/{process_date}/ (after any ORG_UNIT prefix). These markers "
        "are unconditional: they are written whether or not there are quarantine rows, ensuring "
        "each date prefix exists as a concrete object-store key for downstream tooling. The bad, "
        "aggregated, detailed and flag objects are each written as one object per filename at the "
        "documented paths.",
        "Flag objects are named *.zip.flag. The .zip in the filename is a DXV convention that is "
        "backwards compatible with NetReveal naming (flags historically paired by basename with "
        "envelope_*.zip flows). This stage does NOT write a .zip archive next to those flags — bad "
        "rows and reports are delimiter-separated files and flag bodies are plain text. The .zip "
        "segment exists only in the object name for integration compatibility.",
        "This matters for outbound PGP: handlers that encrypt outbound files often key off paths "
        "ending with .zip. Because acq_success_* and envelope_error_* objects are named "
        "*.zip.flag, the path ends with .flag (not .zip), so they are NOT treated as zip payloads "
        "by that branch and are handled like other non-.zip objects.",
    ],
    "context": [
        (".keep markers", "Three zero-byte objects per run under bad/report/feedback date prefixes."),
        ("Unconditional", "Written before per-table exports, regardless of quarantine rows."),
        ("Single keys", "bad, aggregated, detailed and flag objects: one object per filename."),
        (".zip.flag convention", "DXV/NetReveal-compatible naming; no companion .zip archive is written."),
        ("PGP routing", "Path ends with .flag not .zip, so flags are handled as non-zip objects."),
    ],
    "acceptance": [
        "Every run writes exactly three .keep objects, one under each of the bad/report/feedback date prefixes (after any ORG_UNIT prefix).",
        ".keep markers are created even when there are zero quarantine rows.",
        ".keep markers are zero-byte and exist before/independent of per-table exports.",
        "Flag object names end with .zip.flag and no companion .zip archive is written alongside.",
        "Each of bad/aggregated/detailed/flag is written as a single object per filename at the documented path.",
        "Because the key ends with .flag (not .zip), the flag is treated as a non-zip object by outbound routing.",
    ],
    "test_data": [
        ("process_date", "20260313"),
        ("bad .keep key", "landing/acquisition/bad/20260313/.keep"),
        ("report .keep key", "landing/acquisition/feedback/reporting/20260313/.keep"),
        ("feedback .keep key", "landing/acquisition/feedback/20260313/.keep"),
        ("flag name", "envelope_error_20260313.zip.flag / acq_success_20260313.zip.flag"),
        ("companion zip", "NONE expected (no *.zip object next to the flag)"),
    ],
    "preconditions": [
        "A clean MinIO prefix for the date (so created objects can be counted unambiguously).",
        "ORG_UNIT set or unset per the individual test.",
    ],
    "tests": [
        {
            "id": "TC-001",
            "title": "Happy path — three .keep markers created (with rows)",
            "type": "Happy Path",
            "priority": "High",
            "objective": "A normal run writes the three date-prefix .keep markers.",
            "steps": [
                step("Run an export that has quarantine rows.",
                     "customer populated; process_date=20260313",
                     "Run completes."),
                step("List objects under each date prefix.",
                     "bad/20260313/, feedback/reporting/20260313/, feedback/20260313/",
                     "Each prefix contains a .keep object (3 total)."),
                step("Verify each .keep object size.",
                     "Inspect content-length",
                     "Each .keep is zero bytes."),
            ],
        },
        {
            "id": "TC-002",
            "title": "Boundary — .keep markers created with NO rows",
            "type": "Boundary",
            "priority": "High",
            "objective": "The markers are unconditional, even when nothing is exported.",
            "steps": [
                step("Run an export with no quarantine rows for any table.",
                     "All sources empty/missing; process_date=20260313",
                     "Run completes (acq_success outcome)."),
                step("List the three date prefixes.",
                     "bad/report/feedback for 20260313",
                     "All three .keep markers still exist despite zero exported data files."),
            ],
        },
        {
            "id": "TC-003",
            "title": "Happy path — .keep markers respect ORG_UNIT prefix",
            "type": "Happy Path",
            "priority": "Medium",
            "objective": "When ORG_UNIT is set, the .keep markers are created under the prefixed paths.",
            "preconditions": ["ORG_UNIT=OrgA"],
            "steps": [
                step("Run with ORG_UNIT set.",
                     "ORG_UNIT=OrgA; process_date=20260313",
                     "Run completes."),
                step("Locate the .keep markers.",
                     "<orgunit-prefix>/.../20260313/.keep",
                     "All three markers exist beneath the ORG_UNIT-prefixed roots."),
            ],
        },
        {
            "id": "TC-004",
            "title": "Happy path — flag named *.zip.flag with no companion .zip",
            "type": "Happy Path",
            "priority": "High",
            "objective": "Flag uses the .zip.flag convention and no .zip archive is written.",
            "steps": [
                step("Run an export with failures.",
                     "customer populated; process_date=20260313",
                     "Run completes."),
                step("Inspect the feedback prefix object names.",
                     "List feedback/20260313/",
                     "envelope_error_20260313.zip.flag exists; there is NO envelope_error_20260313.zip object next to it."),
                step("Confirm flag body is plain text.",
                     "Read the flag object",
                     "Body is plain text (not a zip archive)."),
            ],
        },
        {
            "id": "TC-005",
            "title": "Security/Routing — flag treated as non-zip by outbound handler",
            "type": "Security",
            "priority": "Medium",
            "objective": "Outbound PGP/zip routing keys off '.zip' suffix; '.zip.flag' must be excluded.",
            "steps": [
                step("Apply the outbound routing rule that selects keys ending with '.zip'.",
                     "Routing predicate: key.endswith('.zip')",
                     "Predicate is exercised against the run's objects."),
                step("Evaluate the predicate against the flag key.",
                     "Key: .../envelope_error_20260313.zip.flag",
                     "Predicate is FALSE (key ends with '.flag'); the flag is NOT selected as a zip payload."),
                step("Confirm the flag follows the non-zip handling branch.",
                     "Trace handling",
                     "Flag is handled like other non-.zip objects (not PGP-zipped)."),
            ],
        },
        {
            "id": "TC-006",
            "title": "Negative — re-run does not duplicate single keys",
            "type": "Negative",
            "priority": "Medium",
            "objective": "Re-running for the same date yields one object per filename (overwrite, not duplicate).",
            "steps": [
                step("Run the export twice for the same date.",
                     "Two runs, process_date=20260313, same sources",
                     "Both runs complete."),
                step("Enumerate data/flag objects.",
                     "List keys for 20260313",
                     "Each filename exists exactly once (single object per filename); no duplicate/suffixed variants."),
            ],
        },
    ],
})


# ===========================================================================
# DXV-FRE-009 — Downstream DXV integration & ingest-key alignment
# ===========================================================================
STORIES.append({
    "id": "DXV-FRE-009",
    "filename": "DXV-FRE-009_Downstream-DXV-Integration-and-Ingest-Alignment",
    "title": "Integrate exports with DXV pickup and align resubmit keys with ingest",
    "epic": "Downstream Integration & Round-Trip",
    "labels": ["dxv", "failed-record-export", "ingestion", "integration", "round-trip"],
    "priority": "High",
    "story_points": 5,
    "components": ["failed-record-export", "ingest-to-staging"],
    "persona": "AML operations engineer",
    "want": (
        "the exporter to write flags and data under the roots DXV watches and to produce "
        "clean-bad keys that ingest-to-staging can resubmit without renaming"
    ),
    "benefit": (
        "the failure feedback loop is fully automated end-to-end and corrected records flow "
        "straight back into ingestion"
    ),
    "description": [
        "This stage shares flow-wide MinIO bucket and credentials with the other MinIO-driven "
        "stages (e.g. ingest and validation). DXV (or a similar pickup service) must watch or move "
        "the roots in use — for example landing/acquisition/feedback/ and landing/acquisition/bad/ "
        "with the defaults. Archiving of picked-up files happens downstream on the DXV side and is "
        "not part of this stage. The pipeline runner returns a Python dict summarising the stage.",
        "For the resubmit loop, ingest-to-staging resolves each table's upload from the exact "
        "object key {table_name}_{process_date}.{input.extension} under the ingest prefix. The "
        "clean-bad export key therefore needs to line up with that expected ingest key. If "
        "filenames differ, the operator must rename objects or adjust process_date / the contract "
        "so the key matches.",
        "This story validates the integration seams: credentials reuse, DXV watching the correct "
        "roots, the returned summary dict, and the clean-bad -> ingest key round-trip.",
    ],
    "context": [
        ("Shared MinIO", "Same flow-wide bucket and credentials as ingest and validation stages."),
        ("DXV watch roots", "DXV watches/moves the roots in use (e.g. .../feedback/ and .../bad/)."),
        ("Archiving", "Downstream on the DXV side, not part of this stage."),
        ("Return value", "run_pipeline returns a Python dict summary for the stage."),
        ("Ingest key", "ingest-to-staging resolves {table_name}_{process_date}.{input.extension} under the ingest prefix."),
        ("Mismatch remedy", "Rename objects or adjust process_date / contract so the key matches."),
    ],
    "acceptance": [
        "The stage reads/writes using the same flow-wide MinIO bucket and credentials as other stages (no separate credential set required).",
        "Flags and data land under the roots DXV is configured to watch (defaults: feedback/ and bad/).",
        "run_pipeline returns a Python dict summary describing the run.",
        "A clean-bad object named {table_name}_{process_date}.{ext} is resolvable by ingest-to-staging when the extension matches input.extension.",
        "When export key and ingest-expected key differ, the documented remedy (rename / adjust process_date or contract) makes the round-trip succeed.",
    ],
    "test_data": [
        ("Bucket/credentials", "flow-wide MinIO settings (shared)"),
        ("DXV-watched roots", "landing/acquisition/feedback/, landing/acquisition/bad/"),
        ("Clean-bad key", "landing/acquisition/bad/20260313/customer_20260313.csv"),
        ("Ingest-expected key", "<ingest prefix>/customer_20260313.csv  (input.extension=csv)"),
        ("Return value", "Python dict (tables processed, objects written, flag emitted, ...)"),
    ],
    "preconditions": [
        "Flow-wide MinIO bucket/credentials are configured and shared across stages.",
        "A DXV (or stub) pickup watcher is configured against the roots under test.",
        "ingest-to-staging is available to validate the resubmit key round-trip.",
    ],
    "tests": [
        {
            "id": "TC-001",
            "title": "Happy path — shared MinIO credentials reused",
            "type": "Happy Path",
            "priority": "High",
            "objective": "The stage uses the flow-wide bucket/credentials with no separate config.",
            "steps": [
                step("Configure only the flow-wide MinIO settings (as used by ingest/validation).",
                     "Shared bucket + credentials; no export-specific credential override",
                     "Settings present."),
                step("Run the export.",
                     "process_date=20260313; table=customer",
                     "Run completes; objects written to the shared bucket without extra credentials."),
            ],
        },
        {
            "id": "TC-002",
            "title": "Happy path — DXV picks up flag + data from watched roots",
            "type": "Happy Path",
            "priority": "High",
            "objective": "Objects land under the DXV-watched roots and are detected by the pickup watcher.",
            "steps": [
                step("Configure DXV (or stub) to watch the feedback and bad roots.",
                     "Watch landing/acquisition/feedback/ and landing/acquisition/bad/",
                     "Watcher active."),
                step("Run an export with failures.",
                     "customer populated; process_date=20260313",
                     "Run completes; envelope_error flag + clean-bad written under watched roots."),
                step("Observe DXV pickup.",
                     "Watcher events / moved objects",
                     "DXV detects the flag and data objects under the watched roots."),
            ],
        },
        {
            "id": "TC-003",
            "title": "Happy path — clean-bad key resubmits via ingest-to-staging",
            "type": "Happy Path",
            "priority": "High",
            "objective": "A clean-bad object is resolvable by ingest using the exact key pattern.",
            "steps": [
                step("Run the export producing a clean-bad object.",
                     "file_format=csv (input.extension=csv); table=customer; process_date=20260313",
                     "customer_20260313.csv written."),
                step("Place/point the clean-bad object at the ingest prefix.",
                     "Key {table_name}_{process_date}.{input.extension} under ingest prefix",
                     "Key matches the ingest-expected pattern."),
                step("Run ingest-to-staging for the same table/date.",
                     "ingest-to-staging, customer, 20260313",
                     "Ingest resolves and loads the object without renaming."),
            ],
        },
        {
            "id": "TC-004",
            "title": "Negative — key mismatch blocks resubmit until remedied",
            "type": "Negative",
            "priority": "Medium",
            "objective": "A mismatched key is not silently ingested; the documented remedy fixes it.",
            "steps": [
                step("Create an export key that does not match ingest expectations.",
                     "Export ext .pipe but input.extension=csv (key customer_20260313.pipe)",
                     "Keys differ."),
                step("Run ingest-to-staging.",
                     "ingest-to-staging, customer, 20260313",
                     "Ingest does NOT resolve the mismatched key (no silent load)."),
                step("Apply the documented remedy and re-run.",
                     "Rename to customer_20260313.csv OR align contract/file_format",
                     "After remedy, ingest resolves and loads the object."),
            ],
        },
        {
            "id": "TC-005",
            "title": "Happy path — return value summary is well-formed",
            "type": "Happy Path",
            "priority": "Medium",
            "objective": "run_pipeline returns a usable dict summary for orchestration.",
            "steps": [
                step("Run the export and capture the return value.",
                     "result = run_pipeline(\"failed-record-export\", ...)",
                     "result is a Python dict."),
                step("Inspect the summary contents.",
                     "result keys/values",
                     "Dict conveys the run outcome (e.g. tables processed/skipped, objects written, flag type) usable by an orchestrator."),
            ],
        },
        {
            "id": "TC-006",
            "title": "Happy path — archiving is downstream (not this stage)",
            "type": "Happy Path",
            "priority": "Low",
            "objective": "This stage does not archive picked-up files; that is DXV's responsibility.",
            "steps": [
                step("Run the export and let DXV pick up the objects.",
                     "process_date=20260313",
                     "Objects written and picked up."),
                step("Verify this stage performs no archiving itself.",
                     "Inspect stage actions/logs",
                     "No archive step is performed by failed-record-export; archiving is observed only on the DXV side."),
            ],
        },
    ],
})


# ===========================================================================
# DXV-FRE-010 — Non-functional requirements
# ===========================================================================
STORIES.append({
    "id": "DXV-FRE-010",
    "filename": "DXV-FRE-010_Non-Functional-Requirements",
    "title": "Validate non-functional qualities of the quarantine export stage",
    "epic": "Non-Functional Quality",
    "labels": ["dxv", "failed-record-export", "non-functional", "performance", "security", "reliability"],
    "priority": "High",
    "story_points": 8,
    "components": ["failed-record-export"],
    "persona": "Test Engineering Manager",
    "want": (
        "the export stage to meet performance, scalability, reliability/idempotency, security and "
        "compatibility expectations under realistic conditions"
    ),
    "benefit": (
        "the quarantine feedback loop is dependable and safe at production scale, not just "
        "functionally correct on small inputs"
    ),
    "description": [
        "Beyond functional correctness, the failed-record-export stage must behave well under "
        "production conditions. This story groups the non-functional checks: throughput and "
        "latency on large quarantine volumes, scaling across many contract tables, idempotent "
        "re-runs for the same process_date, resilience to transient MinIO/Iceberg errors, "
        "security of credentials and the outbound PGP routing contract, and backwards "
        "compatibility with DXV / NetReveal naming.",
        "These tests rely on the documented behaviours of the stage (single object per filename, "
        "unconditional .keep markers, *.zip.flag naming, shared flow-wide credentials, and the "
        "one-flag-per-run envelope rule) and assert the quality attributes around them.",
        "Targets below are representative acceptance thresholds for the suite; calibrate the exact "
        "numbers to the deployment's SLAs before execution.",
    ],
    "context": [
        ("Performance", "Time to export a large quarantine volume within an agreed window."),
        ("Scalability", "Behaviour as the number of contract tables and total rows grows."),
        ("Reliability/Idempotency", "Re-running the same date converges to one object per filename."),
        ("Security", "Credential handling and the .zip-suffix outbound routing contract."),
        ("Compatibility", "DXV / NetReveal-compatible flag naming and trigger payloads."),
        ("Observability", "The returned summary dict and logs make outcomes auditable."),
    ],
    "acceptance": [
        "A large single-table quarantine export completes within the agreed performance window and memory budget.",
        "Throughput scales acceptably as the number of contract tables increases (no super-linear degradation).",
        "Re-running the same process_date is idempotent: one object per filename, consistent flag outcome.",
        "Transient MinIO/Iceberg errors are retried or fail cleanly without leaving partial/duplicate objects.",
        "Credentials are never written into exported objects, flags, logs or object keys.",
        "Outbound routing keyed on '.zip' never selects '*.zip.flag' objects (handled as non-zip).",
        "Flag naming remains DXV/NetReveal compatible and the acq_success payload is a single newline.",
    ],
    "test_data": [
        ("Large volume", "1,000,000 quarantine rows in one table"),
        ("Many tables", "50 contract tables for one process_date"),
        ("Perf target (example)", "<= 10 min wall-clock; stable, bounded memory"),
        ("Retry scenario", "Inject transient 5xx / connection reset on MinIO put"),
        ("Sensitive values", "MinIO access key / secret must never appear in outputs"),
        ("process_date", "20260313"),
    ],
    "preconditions": [
        "A representative non-prod environment sized close to production.",
        "Ability to seed large quarantine volumes and to inject transient object-store faults.",
        "Agreed SLA thresholds to assert against (substitute real numbers for the examples).",
    ],
    "tests": [
        {
            "id": "TC-001",
            "title": "Performance — large single-table export within window",
            "type": "Non-Functional",
            "priority": "High",
            "objective": "Exporting a very large quarantine table meets the agreed time/memory budget.",
            "steps": [
                step("Seed a large quarantine table.",
                     "customer: 1,000,000 rows with mixed validation_errors",
                     "Table populated at scale."),
                step("Run the export and measure wall-clock + peak memory.",
                     "process_date=20260313; capture timing & memory",
                     "Run completes within the agreed window (example <= 10 min) with bounded memory (no OOM)."),
                step("Verify output completeness.",
                     "Counts in bad/detailed vs source; aggregated totals",
                     "All rows accounted for; aggregated counts reconcile to source."),
            ],
        },
        {
            "id": "TC-002",
            "title": "Scalability — many contract tables in one run",
            "type": "Non-Functional",
            "priority": "Medium",
            "objective": "Throughput degrades at most linearly as table count grows.",
            "steps": [
                step("Seed many tables with moderate row counts.",
                     "50 tables x ~10k rows each; process_date=20260313",
                     "All tables populated."),
                step("Run the export and record per-table and total timing.",
                     "Measure total + per-table durations",
                     "Total time scales ~linearly with table count; no pathological slowdown or memory growth."),
                step("Verify all tables exported and one flag emitted.",
                     "List objects; inspect flag",
                     "Each table has its files; exactly one envelope_error flag aggregates all failing tables."),
            ],
        },
        {
            "id": "TC-003",
            "title": "Reliability — idempotent re-run for same date",
            "type": "Non-Functional",
            "priority": "High",
            "objective": "Re-running the same process_date does not duplicate objects or flip the flag.",
            "steps": [
                step("Run the export once and snapshot the object listing.",
                     "process_date=20260313; record keys + checksums",
                     "Baseline captured."),
                step("Re-run the export with identical inputs.",
                     "process_date=20260313 again",
                     "Run completes."),
                step("Compare object listings.",
                     "Diff keys vs baseline",
                     "Same set of keys (one object per filename); .keep markers and flag outcome unchanged."),
            ],
        },
        {
            "id": "TC-004",
            "title": "Reliability — transient object-store fault handling",
            "type": "Non-Functional",
            "priority": "High",
            "objective": "A transient MinIO error does not leave partial or duplicate objects.",
            "steps": [
                step("Inject a transient fault during writes.",
                     "Simulate 5xx / connection reset on a subset of put operations",
                     "Fault injected."),
                step("Run the export.",
                     "process_date=20260313",
                     "Stage retries or fails cleanly (documented behaviour)."),
                step("Inspect resulting object state.",
                     "List keys; verify integrity",
                     "No partially-written/duplicate objects remain; on success, one object per filename; on clean failure, state is recoverable by re-run."),
            ],
        },
        {
            "id": "TC-005",
            "title": "Security — no credential leakage into outputs",
            "type": "Security",
            "priority": "Highest",
            "objective": "MinIO credentials never appear in objects, flags, keys or logs.",
            "steps": [
                step("Run the export with known credential values configured.",
                     "Access key / secret set to recognisable sentinel values",
                     "Run completes."),
                step("Scan all outputs and logs for the sentinels.",
                     "grep object bodies, flag bodies, object keys, run logs",
                     "Sentinel credential values are NOT present anywhere in outputs or logs."),
            ],
        },
        {
            "id": "TC-006",
            "title": "Security — outbound PGP routing excludes *.zip.flag",
            "type": "Security",
            "priority": "High",
            "objective": "The '.zip'-suffix outbound branch must not select flag objects.",
            "steps": [
                step("Run an export that emits a flag.",
                     "process_date=20260313 with failures",
                     "envelope_error_20260313.zip.flag written."),
                step("Apply the outbound selection rule keyed on '.zip'.",
                     "Predicate: path ends with '.zip'",
                     "Flag key ends with '.flag' -> predicate FALSE; flag is not PGP/zip-routed."),
            ],
        },
        {
            "id": "TC-007",
            "title": "Compatibility — DXV/NetReveal naming & trigger payload",
            "type": "Non-Functional",
            "priority": "Medium",
            "objective": "Flag names and acq_success payload remain backwards compatible.",
            "steps": [
                step("Run both a clean and a failing scenario.",
                     "One run no failures, one run with failures; process_date=20260313",
                     "Both complete."),
                step("Verify flag names match the DXV/NetReveal convention.",
                     "acq_success_20260313.zip.flag and envelope_error_20260313.zip.flag",
                     "Names match exactly; *.zip.flag convention preserved."),
                step("Verify the acq_success payload.",
                     "Read success flag bytes",
                     "Body is exactly a single newline (trigger compatibility preserved)."),
            ],
        },
        {
            "id": "TC-008",
            "title": "Observability — auditable run summary",
            "type": "Non-Functional",
            "priority": "Medium",
            "objective": "The returned dict and logs make the run outcome auditable.",
            "steps": [
                step("Run a mixed scenario and capture return value + logs.",
                     "Some tables fail, some skipped; process_date=20260313",
                     "Run completes."),
                step("Review the summary and logs.",
                     "result dict + log lines",
                     "Outcome is auditable: which tables exported/skipped, object counts, and which flag was emitted are all discernible."),
            ],
        },
    ],
})


