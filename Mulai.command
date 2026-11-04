#!/bin/zsh
cd "$(dirname "$0")"
set -e
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi
if ! .venv/bin/python -c 'import flask, yt_dlp, imageio_ffmpeg, faster_whisper' >/dev/null 2>&1; then
  .venv/bin/python -m pip install -r requirements.txt
fi
if [ ! -x runtime/node_modules/node/bin/node ]; then
  npm --cache "$PWD/.npm-cache" --prefix runtime install --no-audit --no-fund
fi
.venv/bin/python serverctl.py start
open http://127.0.0.1:8765
echo "Server berjalan di latar belakang. Terminal ini boleh ditutup."
