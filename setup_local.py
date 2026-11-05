"""Reproducible local setup and read-only diagnostics, using only the stdlib."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from urllib.request import build_opener, ProxyHandler

ROOT = Path(__file__).resolve().parent
IMPORTS = 'flask yt_dlp imageio_ffmpeg faster_whisper av cv2 langdetect'.split()

class SetupError(RuntimeError): pass


def probe_python(command):
    try:
        result = subprocess.run([*command,'-c','import sys,json; print(json.dumps(list(sys.version_info[:2])))'],capture_output=True,text=True)
        version = json.loads(result.stdout) if result.returncode == 0 else []
        return len(version)==2 and version[0]==3 and 11<=version[1]<=13
    except (OSError,ValueError,TypeError): return False


def select_python():
    for executable in ['python3.13','python3.12','python3.11',sys.executable,'python3']:
        if probe_python([executable]): return executable
    raise SetupError('Python 3.11–3.13 belum ditemukan. Pasang Python 3.13 (macOS Homebrew: brew install python@3.13), lalu ulangi setup. Python 3.14+ belum didukung pin dependensi proyek.')


def run(args):
    result = subprocess.run([str(arg) for arg in args],cwd=ROOT)
    if result.returncode: raise SetupError(f'Perintah gagal (exit {result.returncode}). Perbaiki error di atas lalu ulangi; setup aman diulang.')


def venv_python(): return ROOT/'.venv'/('Scripts/python.exe' if sys.platform=='win32' else 'bin/python')


def imports_ready(python):
    try: return subprocess.run([str(python),'-c','import '+', '.join(IMPORTS)],capture_output=True).returncode == 0
    except OSError: return False


def sync_dependencies(python):
    requirements = ROOT/'requirements.txt'
    signature = hashlib.sha256(requirements.read_bytes()).hexdigest()
    marker = ROOT/'.venv/.klip-requirements.sha256'
    recorded = marker.read_text().strip() if marker.exists() else ''
    if recorded != signature or not imports_ready(python):
        run([python,'-m','pip','install','-r',requirements])
        if not imports_ready(python): raise SetupError('Dependensi belum dapat diimpor setelah instalasi. Periksa versi Python dan output pip.')
        marker.write_text(signature)
    else: print('Dependensi Python sesuai requirements; tidak dipasang ulang.',flush=True)


def node_ready(node):
    try:
        result=subprocess.run([str(node),'--version'],capture_output=True,text=True)
        return result.returncode==0 and result.stdout.strip().startswith('v22.')
    except OSError: return False


def setup():
    if sys.platform != 'darwin':
        raise SetupError('Setup aplikasi saat ini ditargetkan untuk macOS. Windows/Linux belum didukung end-to-end; lihat docs/NEW_MACHINE.md. Tidak ada paket yang dipasang.')
    python = venv_python()
    if python.exists():
        if not probe_python([str(python)]):
            raise SetupError('Python pada .venv tidak kompatibel. Simpan/rename .venv lama, pasang Python 3.11–3.13 lalu ulangi. Setup tidak menghapus environment atau data.')
    else:
        executable = select_python()
        print(f'Membuat environment dengan {executable}…',flush=True)
        run([executable,'-m','venv',ROOT/'.venv'])
    sync_dependencies(python)
    node = ROOT/'runtime/node_modules/node/bin/node'
    if not node_ready(node):
        npm = shutil.which('npm')
        if not npm: raise SetupError('npm belum ditemukan. Pasang Node.js/npm, lalu buka ulang Terminal dan ulangi setup.')
        run([npm,'--cache',ROOT/'.npm-cache','--prefix',ROOT/'runtime','ci','--no-audit','--no-fund'])
        if not node_ready(node):
            raise SetupError('Node 22 proyek belum dapat dijalankan. Periksa pesan npm dan apakah install script paket node diblokir; lihat docs/NEW_MACHINE.md.')
    print('Setup aplikasi selesai. Lanjut: npm run setup:ai, lalu npm run doctor dan npm run dev.',flush=True)
    return python


def doctor(skip_ai=False):
    checks=[]
    def check(name,ok,detail):
        checks.append(ok);print(f'{"OK" if ok else "BELUM SIAP"} — {name}: {detail}')
    check('Platform',sys.platform=='darwin',f'{platform.system()} {platform.machine()}; target teruji macOS Apple Silicon')
    python = venv_python()
    check('Python environment',python.exists() and probe_python([str(python)]),'butuh .venv dengan Python 3.11–3.13; npm run setup')
    check('Dependensi Python',python.exists() and imports_ready(python),'Flask, downloader, Whisper, PyAV, FFmpeg package, OpenCV')
    node=ROOT/'runtime/node_modules/node/bin/node'
    check('Runtime Node proyek',node_ready(node),'Node 22; dipasang melalui npm run setup')
    try:
        if sys.platform=='darwin':
            memory=int(subprocess.check_output(['sysctl','-n','hw.memsize'],text=True))
        else: memory=os.sysconf('SC_PAGE_SIZE')*os.sysconf('SC_PHYS_PAGES')
        gib=memory/1024**3
        print(f'INFO — RAM {gib:.1f} GiB; Qwen3 1.7B telah diuji pada RAM 8 GB. Kapasitas tersedia dan kecepatan dapat berbeda.')
    except (OSError,ValueError,AttributeError): print('INFO — RAM tidak dapat dideteksi; lihat rekomendasi di docs/NEW_MACHINE.md.')
    try:
        gib=shutil.disk_usage(ROOT).free/1024**3
        check('Ruang kosong',gib>=4,f'{gib:.1f} GiB; ambang kesiapan 4 GiB, video panjang memerlukan lebih banyak')
    except OSError as exc: check('Ruang kosong',False,str(exc))
    if not skip_ai:
        try:
            opener=build_opener(ProxyHandler({}))
            with opener.open('http://127.0.0.1:11434/api/tags',timeout=3) as response: tags=json.load(response)
            check('Ollama lokal',True,'127.0.0.1:11434; tidak memulai service dari doctor')
            ready=any(model.get('name')=='qwen3:1.7b' for model in tags.get('models',[]))
            check('Model caption',ready,'qwen3:1.7b; jalankan npm run setup:ai jika belum tersedia')
        except (OSError,ValueError,AttributeError):
            check('Ollama/model caption',False,'pasang/buka Ollama lalu npm run setup:ai; lihat docs/LOCAL_AI.md')
    print('Whisper base diunduh pada pemrosesan pertama jika belum ada cache. Doctor tidak mengunduh model atau melakukan inferensi.')
    return 0 if all(checks) else 1


def main():
    # Finder can launch with a minimal PATH; extend only this setup process.
    if sys.platform=='darwin':
        os.environ['PATH']=os.environ.get('PATH','')+os.pathsep+'/opt/homebrew/bin'+os.pathsep+'/usr/local/bin'
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['setup','ai','doctor'])
    parser.add_argument('--skip-ai',action='store_true',help='doctor hanya memeriksa kebutuhan video dasar')
    args=parser.parse_args()
    try:
        if args.action=='doctor': return doctor(args.skip_ai)
        python=setup()
        if args.action=='ai': run([python,ROOT/'local_caption.py'])
        return 0
    except (SetupError,OSError) as exc:
        print(f'Setup belum selesai: {exc}',file=sys.stderr)
        return 1

if __name__=='__main__': raise SystemExit(main())
