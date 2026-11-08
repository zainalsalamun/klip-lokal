#!/usr/bin/env bash
set -euo pipefail
if [[ $(uname -s) != Linux || $(uname -m) != x86_64 || $(id -u) != 0 ]]; then
    echo "Installer ini membutuhkan Linux x86_64 dan root. Target deployment Ubuntu 24.04."
    exit 1
fi
cd /opt/kelip
for command in python3 npm systemctl curl; do
    command -v "$command" >/dev/null
done
python3 - <<'PY'
import sys
if not (sys.version_info.major == 3 and 11 <= sys.version_info.minor <= 13):
    raise SystemExit("Pasang Python 3.11–3.13 terlebih dahulu.")
PY
bash deploy/check-idle.sh
if systemctl is-active --quiet kelip.service; then
    systemctl stop kelip.service
fi
if ! id kelip >/dev/null 2>&1; then
    useradd --system --user-group --home-dir /var/lib/kelip --shell /usr/sbin/nologin kelip
fi
install -d -m 0700 -o kelip -g kelip /opt/kelip/data /var/lib/kelip /var/cache/kelip
python3 -m venv .venv
.venv/bin/python -m pip install -r deploy/requirements.txt
.venv/bin/python -m pip check
npm ci --prefix runtime --no-audit --no-fund
runtime/node_modules/node/bin/node --version
install -m 0644 deploy/kelip.service /etc/systemd/system/kelip.service
install -m 0644 deploy/kelip-workload.slice /etc/systemd/system/kelip-workload.slice
if systemctl cat ollama.service >/dev/null 2>&1; then
    install -d /etc/systemd/system/ollama.service.d
    install -m 0644 deploy/ollama.conf /etc/systemd/system/ollama.service.d/kelip.conf
    echo "Konfigurasi Ollama terpasang. Restart Ollama setelah memastikan tidak ada inferensi aktif."
fi
systemctl daemon-reload
systemctl enable kelip.service
bash deploy/restart.sh
