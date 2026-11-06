#!/bin/zsh
cd "$(dirname "$0")"
set -e
python3 -m kelip.setup_local setup
.venv/bin/python -m kelip.serverctl start
open http://127.0.0.1:8765
echo "Server berjalan di latar belakang. Terminal ini boleh ditutup."
