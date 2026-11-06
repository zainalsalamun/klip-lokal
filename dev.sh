#!/bin/zsh
set -e
cd "$(dirname "$0")"
python3 -m kelip.setup_local setup
# Stop only the managed local server, and refuse if it is processing a video.
.venv/bin/python -m kelip.serverctl stop
echo "Kelip Studio — http://127.0.0.1:8765"
echo "Log tampil di Terminal ini. Tekan Ctrl+C untuk berhenti."
exec .venv/bin/python -u -m kelip.app
