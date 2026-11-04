#!/bin/zsh
set -e
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi
if ! .venv/bin/python -c 'import flask, yt_dlp, imageio_ffmpeg, faster_whisper' >/dev/null 2>&1; then
  .venv/bin/python -m pip install -r requirements.txt
fi
if [ ! -x runtime/node_modules/node/bin/node ]; then
  npm --cache "$PWD/.npm-cache" --prefix runtime install --no-audit --no-fund
fi
# Stop only the managed local server, and refuse if it is processing a video.
.venv/bin/python serverctl.py stop
echo "Klip lokal — http://127.0.0.1:8765"
echo "Log tampil di Terminal ini. Tekan Ctrl+C untuk berhenti."
exec .venv/bin/python -u app.py
