#!/usr/bin/env bash
set -euo pipefail

WEB_URL="${WEB_URL:-http://localhost:3003}"
API_URL="${API_URL:-http://localhost:8008}"

echo "[1/4] Checking FastAPI health: ${API_URL}/health"
curl -fsS "${API_URL}/health" >/tmp/nailai_api_health.json
cat /tmp/nailai_api_health.json
echo

echo "[2/4] Checking web app reachable: ${WEB_URL}"
curl -fsS -I "${WEB_URL}" | head -n 1

echo "[3/4] Checking web->api proxy: ${WEB_URL}/api/v1/styles"
curl -fsS "${WEB_URL}/api/v1/styles" >/tmp/nailai_web_proxy_styles.json
python3 - <<'PY'
import json
from pathlib import Path
data = json.loads(Path("/tmp/nailai_web_proxy_styles.json").read_text())
styles = data.get("styles", [])
print(f"styles_count={len(styles)}")
print(f"sample_style_id={(styles[0].get('id') if styles else 'N/A')}")
PY

echo "[4/4] Checking generated-asset proxy (may be 404 if no generated file yet)"
if curl -fsS -I "${WEB_URL}/generated" >/tmp/nailai_generated_head.txt 2>/dev/null; then
  head -n 1 /tmp/nailai_generated_head.txt
else
  echo "generated endpoint reachable via rewrite check skipped (no file yet)."
fi

echo "OK: core connectivity checks passed."
