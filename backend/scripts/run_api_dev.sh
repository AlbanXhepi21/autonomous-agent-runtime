#!/usr/bin/env bash
# Keep generated runtime files out of the source-reload watch set. Analytics Python
# creates short-lived bootstrap/payload files under workspace/ during a run.
if ! python -c 'import sqlalchemy' >/dev/null 2>&1; then
  echo "Backend dependencies are missing from the active Python environment." >&2
  echo "Run: python -m pip install -e '.[dev]' from backend/" >&2
  exit 1
fi

exec python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --reload --reload-dir app \
  --reload-exclude 'var/**' \
  --reload-exclude '.venv/**'
