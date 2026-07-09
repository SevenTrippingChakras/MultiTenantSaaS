#!/usr/bin/env bash
# Run the backend in dev mode with hot-reload (native, not Docker).
set -euo pipefail
cd "$(dirname "$0")/../backend"
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
