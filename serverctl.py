"""Local macOS service controller; no login item is installed."""
from pathlib import Path
import json, os, socket, subprocess, sys, time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
LABEL = "local.klip.server"
URL = "http://127.0.0.1:8765"
LOG = ROOT / "data" / "server.log"

def health():
    try:
        with urlopen(URL + "/api/health", timeout=1) as response:
            result = json.load(response)
            return result if result.get("app") == "klip-lokal" else None
    except Exception:
        return None

def registered():
    return subprocess.run(["launchctl", "list", LABEL], capture_output=True).returncode == 0

def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    if action == "status":
        state = health()
        print(json.dumps(state, ensure_ascii=False) if state else "Server tidak berjalan.")
        return 0 if state else 1
    if action == "stop":
        state = health()
        if state and state.get("active_jobs"):
            print("Ada video sedang diproses. Tunggu sampai selesai sebelum menghentikan server.")
            return 1
        if registered():
            subprocess.run(["launchctl", "remove", LABEL], check=True)
            for _ in range(30):
                if not health(): break
                time.sleep(.1)
            print("Server dihentikan.")
            return 0
        print("Tidak ada server yang dikelola launcher. Hentikan server manual dengan Control-C di Terminal asalnya.")
        return 0 if not state else 1
    if action != "start":
        print("Usage: python serverctl.py start|stop|status")
        return 2
    if health():
        print("Server siap: " + URL)
        return 0
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 8765)) == 0:
            print("Port 8765 dipakai proses lain atau versi server lama. Hentikan proses itu sebelum mulai.")
            return 1
    if registered():
        subprocess.run(["launchctl", "remove", LABEL], check=True)
    LOG.parent.mkdir(exist_ok=True)
    subprocess.run(["launchctl", "submit", "-l", LABEL, "-o", str(LOG), "-e", str(LOG), "--", str(ROOT / ".venv/bin/python"), str(ROOT / "app.py")], check=True)
    for _ in range(100):
        if health():
            print("Server siap: " + URL)
            print("Log: " + str(LOG))
            return 0
        time.sleep(.2)
    print("Server belum siap. Periksa " + str(LOG))
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
