#!/usr/bin/env bash
set -euo pipefail
if [[ $(id -u) != 0 ]]; then
    echo "Jalankan dengan sudo bash deploy/restart.sh."
    exit 1
fi
cd /opt/kelip
bash deploy/check-idle.sh
systemctl restart kelip.service
for ((attempt=0; attempt<30; attempt++)); do
    if curl --noproxy '*' -fsS --max-time 2 http://127.0.0.1:8765/api/health; then
        exit 0
    fi
    sleep 1
done
echo "Server belum siap. Periksa journalctl -u kelip.service."
exit 1
