#!/usr/bin/env bash
set -euo pipefail

DIR="${1:-build/web}"
cd "$DIR"

# Minimal structure checks
ls -1 *.html >/dev/null
ls -1 *.wasm >/dev/null || true
ls -1 *.pck >/dev/null || true

python3 -m http.server 8000 >/tmp/web_smoke.log 2>&1 &
PID=$!
trap "kill $PID" EXIT

sleep 1
curl -fsS "http://localhost:8000/" >/dev/null
echo "Web smoke: OK (served http://localhost:8000/)"
