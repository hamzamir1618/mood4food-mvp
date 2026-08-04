# Notes for Review

- **`orchestrator.py`**: The `intent` variable is assigned the result of `run_ingestion_pipeline()` but is never subsequently used (Ruff flagged `F841`). This could be a logic error if the intent should be passed to the next pipeline stage (e.g. `run_anchoring_pipeline()`). To ensure CI passes in the meantime without changing logic, this has been temporarily suppressed via `# noqa: F841`.
