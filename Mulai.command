#!/bin/zsh
cd "$(dirname "$0")"
set -e
python3 setup_local.py setup
.venv/bin/python serverctl.py start
open http://127.0.0.1:8765
echo "Server berjalan di latar belakang. Terminal ini boleh ditutup."
