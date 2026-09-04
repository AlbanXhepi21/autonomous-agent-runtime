# Report invariants

Load this only for report templates, publishing, renderers, evidence, charts, or artifacts.

- Publishing and saved/scheduled report execution must not reach `app.llm`.
- Renderers consume compiled reports and pre-rasterized chart images; they must not read run-level facts or choose report content.
- Preserve workspace-scoped report/artifact access and existing evidence provenance. Keep unresolved evidence separate from resolved evidence.
- Use report/unit/API tests first. For output changes, run `cd backend && .venv/bin/python -m scripts.preview_reports [output_dir]` when visual layout matters.

For exact restrictions and accepted rendering inputs, read [reporting](../../../../docs/architecture/reporting.md) and `backend/tests/contracts/test_report_boundaries.py`.
