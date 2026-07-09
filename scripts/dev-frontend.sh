#!/usr/bin/env bash
# Run the frontend Vite dev server with hot-reload.
set -euo pipefail
cd "$(dirname "$0")/../frontend"
npm run dev
