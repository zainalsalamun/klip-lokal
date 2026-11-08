#!/usr/bin/env bash
set -euo pipefail
if systemctl is-active --quiet kelip.service; then
    /opt/kelip/.venv/bin/python - <<'PY'
import json
from urllib.request import urlopen
try:
    with urlopen("http://127.0.0.1:8765/api/health", timeout=5) as response:
        state = json.load(response)
    if state.get("app") != "klip-lokal":
        raise RuntimeError("Identitas server tidak cocok.")
    if state.get("active_jobs") or state.get("active_caption") or state.get("active_exports"):
        raise RuntimeError("Ada pekerjaan aktif. Tunggu selesai sebelum update atau restart.")
except Exception as exc:
    raise SystemExit(f"Operasi dibatalkan. {exc}")
PY
fi
