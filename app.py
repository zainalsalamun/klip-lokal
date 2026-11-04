from pathlib import Path
import json, math, re, subprocess, threading, uuid, os
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
from urllib.parse import urlparse
from flask import Flask, request, jsonify, send_from_directory, render_template, redirect
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024**3
jobs = {}
lock = threading.Lock()
model_lock = threading.Lock()
model = None

def run(args):
    result = subprocess.run([FFMPEG, "-hide_banner", "-y", *map(str,args)], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError("Pemrosesan video gagal: " + result.stderr[-1200:])

def update(jid, **values):
    with lock:
        jobs[jid].update(values)
        (DATA / jid / "job.json").write_text(json.dumps(jobs[jid], ensure_ascii=False))

def candidates(segments, duration, count):
    pool = []
    hooks = re.compile(r"\b(kenapa|bagaimana|rahasia|ternyata|jangan|penting|cara|kesalahan|why|how|secret|never|mistake|because|jadi|tapi)\b", re.I)
    for i, seg in enumerate(segments):
        start = max(0, seg["start"] - .15)
        selected = [s for s in segments[i:] if s["start"] < start + duration]
        if not selected: continue
        end = min(start + duration, selected[-1]["end"])
        if end-start < min(10, duration*.6): continue
        text = " ".join(s["text"] for s in selected)
        words = re.findall(r"\w+", text.lower())
        density = len(words) / max(1, end-start)
        score = len(hooks.findall(text))*2 + min(density, 3)*2 + len(set(words))/max(len(words),1)*3
        if re.search(r"[?!]",text): score += 1
        pool.append(dict(start=round(start,2), end=round(end,2), text=text, score=round(score,2)))
    chosen = []
    for clip in sorted(pool, key=lambda x:x["score"], reverse=True):
        if all(min(clip["end"],c["end"])-max(clip["start"],c["start"]) <= 0 for c in chosen):
            chosen.append(clip)
        if len(chosen) == count: break
    return chosen

def ass_time(t):
    cs = max(0, round(t*100))
    return f"{cs//360000}:{cs//6000%60:02}:{cs//100%60:02}.{cs%100:02}"

def write_subs(path, segments, start, end):
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,42,&H00FFFFFF,&H000000FF,&H00101010,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,45,45,220,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines=[]
    for s in segments:
        a,b=max(start,s["start"]),min(end,s["end"])
        if b<=a: continue
        words=s["text"].replace("{", "").replace("}", "").replace(chr(92), "").split()
        groups=[words[i:i+8] for i in range(0,len(words),8)]
        for i,g in enumerate(groups):
            x=a-start+(b-a)*i/len(groups); y=a-start+(b-a)*(i+1)/len(groups)
            lines.append(f"Dialogue: 0,{ass_time(x)},{ass_time(y)},Default,,0,0,0,,{' '.join(g)}")
    path.write_text(header+"\n".join(lines),encoding="utf-8")

def process(jid, url, local, duration, count, lang):
    try:
        folder=DATA/jid
        source=local
        title=local.name if local else "Video YouTube"
        if url:
            update(jid,status="Mengunduh video YouTube…",progress=8)
            import yt_dlp
            with yt_dlp.YoutubeDL({"js_runtimes":{"node":{"path":str(ROOT/"runtime/node_modules/node/bin/node")}}, "format":"best[height<=1080][ext=mp4]/best[height<=1080]", "outtmpl":str(folder/"source.%(ext)s"),"noplaylist":True,"quiet":True,"socket_timeout":30,"retries":2,"max_filesize":2*1024**3}) as ydl:
                info=ydl.extract_info(url,download=True)
                source=Path(ydl.prepare_filename(info)); title=info.get("title",title)
        update(jid,title=title,status="Menyiapkan audio…",progress=25)
        audio=folder/"audio.wav"
        run(["-i",source,"-vn","-ac","1","-ar","16000",audio])
        update(jid,status="Mentranskripsi suara (model diunduh saat pertama digunakan)…",progress=35)
        global model
        with model_lock:
            if model is None:
                from faster_whisper import WhisperModel
                model=WhisperModel("base",device="cpu",compute_type="int8",download_root=str(DATA/"models"))
            stream,_=model.transcribe(str(audio),language=None if lang=="auto" else lang,vad_filter=True,beam_size=3)
            segments=[dict(start=s.start,end=s.end,text=s.text.strip()) for s in stream]
        (folder/"transcript.json").write_text(json.dumps(segments,ensure_ascii=False))
        update(jid,status="Mencari kandidat klip dari transkrip…",progress=65)
        selected=candidates(segments,duration,count)
        if not selected: raise RuntimeError("Tidak cukup percakapan untuk membuat klip. Coba video dengan suara yang jelas.")
        clips=[]
        for i,c in enumerate(selected):
            update(jid,status=f"Mengekspor klip {i+1}/{len(selected)}…",progress=70+int(28*i/len(selected)))
            ass=folder/f"clip-{i+1}.ass"; out=folder/f"clip-{i+1}.mp4"
            write_subs(ass,segments,c["start"],c["end"])
            # Pass subtitle file as a relative path to avoid filter-path escaping issues.
            vf="scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,setsar=1,subtitles="+ass.name
            result=subprocess.run([FFMPEG,"-hide_banner","-y","-ss",str(c["start"]),"-i",str(source.resolve()),"-t",str(c["end"]-c["start"]),"-vf",vf,"-c:v","libx264","-preset","veryfast","-crf","23","-c:a","aac","-movflags","+faststart",str(out.resolve())],cwd=folder,capture_output=True,text=True)
            if result.returncode: raise RuntimeError("Ekspor gagal: "+result.stderr[-1200:])
            clips.append({**c,"file":out.name,"url":f"/files/{jid}/{out.name}"})
        update(jid,status="Selesai",progress=100,clips=clips,done=True)
    except Exception as exc:
        update(jid,status="Gagal",error=str(exc),done=True)

@app.errorhandler(413)
def too_large(error): return jsonify(error="File terlalu besar. Batas unggahan 2 GB."),413

@app.get("/api/health")
def health():
    with lock:
        active = sum(not job.get("done") for job in jobs.values())
    return jsonify(app="klip-lokal", status="ok", active_jobs=active)

@app.get("/favicon.ico")
def favicon(): return redirect("/static/favicon.svg", code=302)

@app.get("/")
def index(): return render_template("index.html")

@app.post("/api/jobs")
def create():
    url=request.form.get("url","").strip()
    if url:
        parsed=urlparse(url)
        if parsed.scheme not in ("http","https") or parsed.hostname not in {"youtube.com","www.youtube.com","m.youtube.com","youtu.be"}:
            return jsonify(error="Masukkan link YouTube yang valid."),400
    upload=request.files.get("video")
    if not url and (not upload or not upload.filename): return jsonify(error="Masukkan link atau unggah video."),400
    try:
        duration=int(request.form.get("duration",30)); count=int(request.form.get("count",3))
        if duration not in (15,30,45,60) or count not in (1,3,5): raise ValueError()
        lang=request.form.get("language","auto")
        if lang not in ("auto","id","en"): raise ValueError()
    except ValueError: return jsonify(error="Pengaturan tidak valid."),400
    with lock:
        if any(not j.get("done") for j in jobs.values()): return jsonify(error="Ada video sedang diproses. Tunggu sampai selesai."),409
        jid=uuid.uuid4().hex
        folder=DATA/jid;folder.mkdir()
        jobs[jid]=dict(id=jid,status="Dalam antrean…",progress=0,done=False,clips=[])
    local=None
    if not url:
        local=folder/"source.mp4"
        try: upload.save(local)
        except Exception:
            update(jid,done=True,status="Gagal",error="File tidak dapat disimpan. Periksa ruang disk.")
            return jsonify(error="File tidak dapat disimpan. Periksa ruang disk."),400
    threading.Thread(target=process,args=(jid,url,local,duration,count,lang),daemon=True).start()
    return jsonify(id=jid),202

@app.get("/api/jobs/<jid>")
def status(jid):
    with lock: job=jobs.get(jid)
    if job is None and re.fullmatch(r"[a-f0-9]{32}",jid):
        path=DATA/jid/"job.json"
        if path.exists():
            job=json.loads(path.read_text())
            if not job.get("done"): job.update(done=True,error="Proses terhenti saat aplikasi ditutup. Mulai ulang video.")
    return (jsonify(job),200) if job else (jsonify(error="Proses tidak ditemukan."),404)

@app.get("/files/<jid>/<name>")
def files(jid,name):
    if not re.fullmatch(r"[a-f0-9]{32}",jid) or not re.fullmatch(r"clip-[1-5]\.(mp4|ass)",name): return "Tidak ditemukan",404
    return send_from_directory(DATA/jid,name,as_attachment=request.args.get("download")=="1")

if __name__=="__main__":
    app.run(host="127.0.0.1",port=8765,debug=False)
