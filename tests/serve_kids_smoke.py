"""Serve synthetic Studio Anak fixtures on loopback. No production data/model downloads.

Usage: .venv/bin/python tests/serve_kids_smoke.py --data outputs/kids-smoke/live
Optional --whisper-cache PATH loads an existing model snapshot, read-only.
"""
import argparse
from collections import OrderedDict
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from kelip import app as m

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--data', type=Path, required=True)
parser.add_argument('--port', type=int, default=8877)
parser.add_argument('--whisper-cache', type=Path)
args = parser.parse_args()
root = args.data.resolve()
if root == m.DATA.resolve() or root.is_relative_to(m.DATA.resolve()):
    parser.error('Do not use production data/ for smoke fixtures.')
marker = root / '.klip-smoke-fixture'
if root.exists() and any(root.iterdir()) and not marker.is_file():
    parser.error('Nonempty directory is not an owned smoke fixture.')
root.mkdir(parents=True, exist_ok=True)
marker.touch()
m.DATA = root
m.KIDS_BRIEFS = root / 'kids-briefs'; m.KIDS_BRIEFS.mkdir(exist_ok=True)
m.WATERMARK_ASSETS = root / 'watermark-assets'; m.WATERMARK_ASSETS.mkdir(exist_ok=True)
m.WATERMARK_PRESETS = root / 'watermark-presets.json'
m.jobs = {}; m.history_cache = OrderedDict()
if args.whisper_cache:
    from faster_whisper import WhisperModel
    m.model = WhisperModel(str(args.whisper_cache.resolve()), device='cpu', compute_type='int8', local_files_only=True)
else:
    class NoModelDownload:
        def transcribe(self, *a, **kw):
            raise RuntimeError('Smoke server: use --whisper-cache for existing model; downloads disabled.')
    m.model = NoModelDownload()
jid='b'*32
folder=root/jid
if not folder.exists():
    folder.mkdir()
    now=datetime.now(timezone.utc).isoformat()
    brief={'brief_id':'a'*32,'revision':1,'title':'SMOKE — Warna merah','learning_goal':'Mengenal merah pada benda sekitar',
           'category':'warna','target_duration':15,'outline':'Tunjuk benda merah, sebut warna, lalu ulangi.',
           'asset_notes':'Video warna dan audio sintetis milik penguji; bukan percakapan manusia.',
           'age_band':'3_5','language':'id','idea_id':'warna-01','created_at':now,'updated_at':now}
    m.kids_content.save_brief_atomic(m.KIDS_BRIEFS,brief)
    ass=folder/'fixture.ass'
    m.write_subs(ass,[{'start':0,'end':3,'text':'Fixture subtitle untuk pengujian ekspor.'}],0,3)
    subprocess.run([m.FFMPEG,'-hide_banner','-loglevel','error','-y','-f','lavfi','-i','color=c=red:s=480x854:r=10:d=3',
                    '-f','lavfi','-i','sine=frequency=440:duration=3','-vf','subtitles=fixture.ass',
                    '-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-shortest',str(folder/'clip-1.mp4')],cwd=folder,check=True)
    subprocess.run([m.FFMPEG,'-hide_banner','-loglevel','error','-y','-f','lavfi','-i','color=c=blue:s=160x284:r=10:d=12',
                    '-f','lavfi','-i','anullsrc=r=16000:cl=mono','-t','12','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac',str(root/'silence.mp4')],check=True)
    job={'id':jid,'done':True,'title':'SMOKE — Kandidat warna merah','status':'Selesai','progress':100,'audience':'local',
         'content_profile':'kids','language':'id','duration':15,'count':1,'resolution':'480','created_at':now,'updated_at':now,
         'kids_metadata':{'age_band':'3_5','language':'id','brief_id':brief['brief_id'],'brief_snapshot':brief},
         'clips':[{'clip_id':'c'*32,'file':'clip-1.mp4','url':f'/files/{jid}/clip-1.mp4','start':0,'end':3,
                   'text':'Warna merah dapat ditemukan pada apel dan balok mainan. Hari ini kita mengenal warna merah dengan melihat benda di sekitar. Ini balok merah, berbeda dari balok biru.',
                   'caption':'Mengenal warna merah pada benda sekitar.','caption_source':'manual','caption_revision':1,'metadata_revision':1,
                   'watermark_revision':1,'watermark':dict(m.watermark.DEFAULT_WATERMARK_CONFIG,enabled=True,text='SMOKE',width_ratio=.3)}]}
    m.ensure_clip_ids(job); m.write_job_atomic(jid,job)
print(json.dumps({'fixture_data':str(root),'url':f'http://127.0.0.1:{args.port}/kids','real_whisper':bool(args.whisper_cache)}),flush=True)
m.app.run(host='127.0.0.1',port=args.port,debug=False,use_reloader=False)
