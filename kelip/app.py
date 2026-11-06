from pathlib import Path
import json, math, re, subprocess, threading, uuid, os, copy, shutil
from datetime import datetime, timezone
from collections import OrderedDict
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
from urllib.parse import urlparse
from flask import Flask, request, jsonify, send_from_directory, render_template, redirect, Response
import imageio_ffmpeg
from .global_content import TOPICS, IDEAS, SOURCES
from .subtitle_styles import SUBTITLE_STYLES
from .local_caption import summarize, CaptionUnavailable, UnclearTranscript, inference_lock
from . import watermark
from . import kids_content
from . import clip_exports
from .media_quality import download_options, downloaded_path, probe_media, output_quality, SOURCE_HEIGHTS, ENCODER_PRESET, ENCODER_CRF, SCALE_FLAGS

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
WATERMARK_ASSETS = DATA / "watermark-assets"
WATERMARK_ASSETS.mkdir(exist_ok=True)
WATERMARK_PRESETS = DATA / "watermark-presets.json"
KIDS_BRIEFS = DATA / "kids-briefs"
KIDS_BRIEFS.mkdir(exist_ok=True)
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
app = Flask(__name__, template_folder=str(ROOT / "templates"), static_folder=str(ROOT / "static"))
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024**3
jobs = {}
history_cache = OrderedDict()
lock = threading.RLock()
model_lock = threading.Lock()
model = None
active_export = None
caption_requests = 0
RESOLUTIONS = {"480": (480, 854), "720": (720, 1280), "1080": (1080, 1920)}
KLIP_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "klip-lokal.net")

def ensure_clip_ids(job):
    jid = job.get("id") or "0" * 32
    audience = job.get("audience", "local")
    job.setdefault("content_profile", "general")
    job.setdefault("kids_metadata", None)
    seen = set()
    for i, clip in enumerate(job.get("clips", [])):
        cid = clip.get("clip_id")
        if not cid or cid in seen:
            start = clip.get("start")
            ident = f"{jid}:{round(float(start), 3)}" if start is not None else f"{jid}:index:{i}"
            cid = uuid.uuid5(KLIP_NAMESPACE, ident).hex
            if cid in seen:
                cid = uuid.uuid5(KLIP_NAMESPACE, f"{ident}:{i}").hex
            clip["clip_id"] = cid
        seen.add(cid)
        clip.setdefault("metadata_revision", 1)
        clip.setdefault("caption_revision", clip.get("metadata_revision", 1))
        clip.setdefault("watermark_revision", 1)
        clip.setdefault("caption_source", "ai_local" if clip.get("caption_status") == "ready" else "extractive" if clip.get("caption") else "none")
        clip.setdefault("caption_language", "id" if audience == "local" else "en")
        clip.setdefault("caption_updated_at", job.get("updated_at") or job.get("created_at"))
        if "watermark" not in clip:
            clip["watermark"] = copy.deepcopy(watermark.DEFAULT_WATERMARK_CONFIG)
        elif isinstance(clip["watermark"], dict):
            wm = clip["watermark"]
            if wm.get("type") == "logo" and wm.get("asset_id") and (not wm.get("asset_width") or not wm.get("asset_height")):
                dims = watermark.get_asset_dimensions(WATERMARK_ASSETS, wm["asset_id"])
                if dims:
                    wm["asset_width"], wm["asset_height"] = dims
    return job

def run(args):
    result = subprocess.run([FFMPEG, "-hide_banner", "-y", *map(str,args)], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError("Pemrosesan video gagal: " + result.stderr[-1200:])

def write_job_atomic(jid, job_data):
    path = DATA / jid / "job.json"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(job_data, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)

def save_job(jid):
    write_job_atomic(jid, jobs[jid])


def update(jid, **values):
    with lock:
        jobs[jid].update(values, updated_at=datetime.now(timezone.utc).isoformat())
        save_job(jid)


def make_caption(text, audience="local"):
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    # An extractive, single-sentence suggestion rather than a full transcript.
    sentences = re.split(r"(?<=[.!?])\s+", text)
    useful = [sentence for sentence in sentences if len(sentence.split()) >= 4]
    caption = next(iter(useful), text)
    words = caption.split()
    shortened = len(words) > 16 or len(caption) > 120
    caption = " ".join(words[:16])
    if len(caption) > 120:
        caption = caption[:120].rsplit(" ", 1)[0]
    if shortened:
        caption = caption.rstrip(".,;:!?…") + "…"
    return caption or ("A moment worth sharing." if audience == "global_en" else "Satu momen, banyak cerita.")


def legacy_caption(text, audience="local"):
    """Recognize only the previous generated template; preserve custom captions."""
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(text) > 300:
        text = text[:300].rsplit(" ", 1)[0].rstrip(".,;:!?") + "…"
    if audience == "global_en":
        return (text or "A moment worth sharing.") + "\n\nWhat do you think? Share your take in the comments.\n\n#Shorts #Reels #GlobalStories"
    return (text or "Cuplikan pilihan dari video ini.") + "\n\nApa pendapatmu? Tulis di komentar.\n\n#VideoPendek #Shorts #Reels"


def read_job(jid):
    if not re.fullmatch(r"[a-f0-9]{32}", jid):
        return None
    folder = DATA / jid
    if not folder.is_dir():
        return None
    with lock:
        job = copy.deepcopy(jobs.get(jid))
    if job is None:
        try:
            job = json.loads((folder / "job.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(job, dict):
            return None
        if not job.get("done"):
            job.update(done=True, status="Gagal", error="Proses terhenti saat aplikasi ditutup. Mulai ulang video.")
    if not isinstance(job, dict):
        return None
    job["id"] = jid
    if not job.get("created_at"):
        stamp = folder.stat()
        job["created_at"] = datetime.fromtimestamp(getattr(stamp, "st_birthtime", stamp.st_mtime), timezone.utc).isoformat()
    job.setdefault("schema_version", 2)
    job.setdefault("title", "Video sebelumnya")
    job.setdefault("resolution", "720")
    job.setdefault("audience", "local")
    job.setdefault("topic", "general")
    job.setdefault("subtitle_style", "classic")
    for clip in job.get("clips", []):
        if "caption" not in clip or clip["caption"] == legacy_caption(clip.get("text", ""), job["audience"]):
            clip["caption"] = make_caption(clip.get("text", ""), job["audience"])
        clip.setdefault("audience", job["audience"])
        clip.setdefault("subtitle_style", job["subtitle_style"])
    ensure_clip_ids(job)
    return job


def candidates(segments, duration, count, topic="general", learning_goal=None):
    pool = []
    hooks = re.compile(r"\b(kenapa|bagaimana|rahasia|ternyata|jangan|penting|cara|kesalahan|why|how|secret|never|mistake|because|jadi|tapi)\b", re.I)
    # Prefer sentence endings or audible pauses over an exact duration cutoff.
    segments = [s for s in segments if s["end"] > s["start"] and s["text"].strip()]
    def boundary(index):
        return (index == len(segments)-1 or
                segments[index+1]["start"] - segments[index]["end"] >= .35 or
                bool(re.search(r"[.!?…][\"'”’)]*$", segments[index]["text"].strip())))
    for i, seg in enumerate(segments):
        natural_start = i == 0 or boundary(i-1)
        previous_end = segments[i-1]["end"] if i else 0
        start = max(0, previous_end, seg["start"] - .15)
        target = start + duration
        limit = target + min(6, duration * .2)
        endings = [j for j in range(i, len(segments))
                   if segments[j]["end"] <= limit and
                   segments[j]["end"]-start >= min(10, duration*.6)]
        if not endings: continue
        natural_endings = [j for j in endings if boundary(j)]
        last = min(natural_endings or endings, key=lambda j: abs(segments[j]["end"]-target))
        selected = segments[i:last+1]
        next_start = segments[last+1]["start"] if last+1 < len(segments) else segments[last]["end"] + .15
        end = max(segments[last]["end"], min(next_start, segments[last]["end"] + .15))
        text = " ".join(s["text"] for s in selected)
        words = re.findall(r"\w+", text.lower())
        density = len(words) / max(1, end-start)
        score = len(hooks.findall(text))*2 + min(density, 3)*2 + len(set(words))/max(len(words),1)*3
        if learning_goal:
            goal_words = {w for w in re.findall(r"\w+", learning_goal.lower())
                          if len(w) >= 4 and w not in {"mengenal", "mengenali", "belajar", "tentang", "dengan", "benda", "sekitar", "anak"}}
            score += 3 * len(goal_words.intersection(words))
        if natural_start: score += 3
        if boundary(last): score += 3
        if re.search(r"[?!]",text): score += 1
        if topic != "general":
            score += 2 * sum(bool(re.search(r"\b" + re.escape(keyword) + r"\b", text, re.I)) for keyword in TOPICS[topic])
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

def write_subs(path, segments, start, end, subtitle_style="classic"):
    style = SUBTITLE_STYLES[subtitle_style]["ass"]
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
    header = header.replace("Style: Default," + SUBTITLE_STYLES["classic"]["ass"], "Style: Default," + style)
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

def foreground_height(height, framing_layout):
    return round(height * .4) * 2 if framing_layout == "wide" else height


def render_clip(source, ass, out, start, end, resolution="720", framing_layout="full"):
    width, height = RESOLUTIONS[resolution]
    main_height = foreground_height(height, framing_layout)
    camera = "crop@camera" if framing_layout == "wide" else "crop"
    fg = f"scale={width}:{main_height}:force_original_aspect_ratio=increase:force_divisible_by=2:flags={SCALE_FLAGS},{camera}={width}:{main_height},setsar=1"
    if framing_layout == "wide":
        vf = (f"split[bg][fg];[bg]scale=90:160:force_original_aspect_ratio=increase:"
              f"force_divisible_by=2,crop=90:160,boxblur=8:2,scale={width}:{height},setsar=1[back];"
              f"[fg]{fg}[main];[back][main]overlay=x=0:y=(H-h)/2")
    else:
        vf = fg
    vf += ",subtitles=" + ass.name
    framing = {"mode":"center", "note":"Wajah tidak terdeteksi; crop tengah digunakan."}
    audio = ass.parent / "audio.wav"
    if audio.exists():
        try:
            from .speaker_crop import crop_plan
            points, detected = crop_plan(source, audio, start, end, width, main_height)
            if points:
                commands = ass.with_suffix('.crop.txt')
                commands.write_text("\n".join(f"{time:.6f} {camera} x {x};" for time,x in points))
                vf = f"sendcmd=f={commands.name}," + vf
                framing = {"mode":"speaker_estimate", "note":"Crop mengikuti perkiraan pembicara dari wajah dan gerakan mulut; tinjau sebelum posting.", "face_samples":detected, "camera_motion":"per_frame_damped", "crop_commands":len(points)}
        except Exception as exc:
            framing = {"mode":"center", "note":"Pelacakan tidak tersedia; crop tengah digunakan.", "detail":str(exc)}
    framing["layout"] = framing_layout
    framing["foreground_height"] = main_height
    if framing_layout == "wide":
        framing["note"] = "Crop lebih lebar · latar blur. " + framing["note"]
    framing["quality"] = output_quality(probe_media(source), width, height, foreground_height=main_height)
    framing["encoder"] = {"preset":ENCODER_PRESET, "crf":int(ENCODER_CRF), "scale":SCALE_FLAGS}
    ass.with_suffix('.framing.json').write_text(json.dumps(framing, ensure_ascii=False))
    result = subprocess.run([FFMPEG, "-hide_banner", "-y", "-ss", str(start), "-i", str(source.resolve()),
                             "-t", str(end-start), "-vf", vf, "-c:v", "libx264", "-preset", ENCODER_PRESET,
                             "-crf", ENCODER_CRF, "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart", str(out.resolve())],
                            cwd=ass.parent, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError("Ekspor gagal: " + result.stderr[-1200:])
    return framing


def kids_caption(result):
    text = result.get("caption", "")
    if re.search(r"(?i)komentar|subscribe|berlangganan|beli|alamat|nomor telepon|dijamin|pasti pintar", text):
        raise UnclearTranscript("Caption perlu ditinjau: hindari CTA, data pribadi atau klaim hasil belajar.")
    return result


def process(jid, url, local, duration, count, lang, resolution="720", audience="local", topic="general", subtitle_style="classic", source_quality="1080", framing_layout="full"):
    try:
        folder=DATA/jid
        source=local
        title=jobs[jid].get("title") or (local.name if local else "Video YouTube")
        if url:
            update(jid,status="Mengunduh video YouTube…",progress=8)
            import yt_dlp
            options = download_options(folder, FFMPEG, ROOT/"runtime/node_modules/node/bin/node", source_quality)
            with yt_dlp.YoutubeDL(options) as ydl:
                info=ydl.extract_info(url,download=True)
                source=downloaded_path(ydl, info, folder); title=info.get("title",title)
            if source.stat().st_size > 2*1024**3:
                raise RuntimeError("Sumber gabungan melebihi 2 GB. Pilih kualitas sumber lebih rendah.")
        source_media = probe_media(source)
        update(jid, source_media=source_media)
        update(jid,title=title,status="Menyiapkan audio…",progress=25)
        audio=folder/"audio.wav"
        run(["-i",source,"-vn","-ac","1","-ar","16000",audio])
        update(jid,status="Menerjemahkan subtitle ke bahasa Inggris…" if audience == "global_en" else "Mentranskripsi suara (model diunduh saat pertama digunakan)…",progress=35)
        global model
        with model_lock:
            if model is None:
                from faster_whisper import WhisperModel
                model=WhisperModel("base",device="cpu",compute_type="int8",download_root=str(DATA/"models"))
            stream,_=model.transcribe(str(audio),language=None if lang=="auto" else lang,vad_filter=True,beam_size=3,task="translate" if audience == "global_en" else "transcribe")
            segments=[dict(start=s.start,end=s.end,text=s.text.strip()) for s in stream]
        (folder/"transcript.json").write_text(json.dumps(segments,ensure_ascii=False))
        update(jid,status="Mencari kandidat klip dari transkrip…",progress=65)
        if jobs[jid].get("content_profile") == "kids":
            goal = jobs[jid].get("kids_metadata", {}).get("brief_snapshot", {}).get("learning_goal", "")
            selected = candidates(segments, duration, count, topic, learning_goal=goal)
        else:
            selected = candidates(segments, duration, count, topic)
        if not selected:
            if jobs[jid].get("content_profile") == "kids":
                raise RuntimeError("Ucapan belum cukup jelas untuk kandidat anak. Lagu/gerak perlu pemilihan manual; simpan rencana brief dan gunakan sumber dengan narasi jelas.")
            raise RuntimeError("Tidak cukup percakapan untuk membuat klip. Coba video dengan suara yang jelas.")
        clips=[]
        now_iso = datetime.now(timezone.utc).isoformat()
        for i,c in enumerate(selected):
            update(jid,status=f"Menyesuaikan crop pembicara & mengekspor klip {i+1}/{len(selected)}…",progress=70+int(28*i/len(selected)))
            ass=folder/f"clip-{i+1}.ass"; out=folder/f"clip-{i+1}.mp4"
            write_subs(ass,segments,c["start"],c["end"],subtitle_style)
            framing = render_clip(source, ass, out, c["start"], c["end"], resolution, framing_layout=framing_layout)
            width, height = RESOLUTIONS[resolution]
            clip_id = uuid.uuid5(KLIP_NAMESPACE, f"{jid}:{round(float(c['start']), 3)}").hex
            clips.append({**c,"clip_id":clip_id,"metadata_revision":1,"file":out.name,"url":f"/files/{jid}/{out.name}",
                          "subtitle_style":subtitle_style,"framing":framing,"resolution":resolution,"width":width,"height":height,
                          "quality":output_quality(source_media, width, height, foreground_height=foreground_height(height, framing_layout)),
                          "framing_layout":framing_layout,
                          "caption":make_caption(c["text"],audience),"caption_source":"extractive",
                          "caption_language":"id" if audience == "local" else "en",
                          "caption_updated_at":now_iso,"audience":audience})
        for i, clip in enumerate(clips):
            update(jid,status=f"AI lokal merangkum pembahasan klip {i+1}/{len(clips)}…",progress=98)
            try:
                ai_res = summarize(clip["text"],audience)
                if jobs[jid].get("content_profile") == "kids":
                    ai_res = kids_caption(ai_res)
                clip.update(ai_res)
                clip["caption_source"] = "ai_local"
                clip["caption_updated_at"] = datetime.now(timezone.utc).isoformat()
            except (CaptionUnavailable, UnclearTranscript) as exc:
                clip.update(caption="",caption_source="none",caption_status="needs_review" if isinstance(exc,UnclearTranscript) else "unavailable",caption_note=str(exc))
        update(jid,status="Selesai",progress=100,clips=clips,done=True,schema_version=2)
    except Exception as exc:
        update(jid,status="Gagal",error=str(exc),done=True)

@app.context_processor
def asset_version():
    files = [ROOT / "templates/index.html", ROOT / "static/app.js", ROOT / "static/custom-select.js", ROOT / "static/style.css"]
    return {"asset_version": str(max(file.stat().st_mtime_ns for file in files)), "subtitle_styles":SUBTITLE_STYLES}


@app.errorhandler(413)
def too_large(error):
    message = "Brief terlalu besar. Batas request 32 KiB." if request.path.startswith("/api/kids/briefs") else "File terlalu besar. Batas unggahan 2 GB."
    return jsonify(error=message),413

@app.get("/api/health")
def health():
    with lock:
        active = sum(not job.get("done") for job in jobs.values())
    return jsonify(app="klip-lokal", status="ok", active_jobs=active + int(active_export is not None), active_exports=int(active_export is not None), active_caption=inference_lock.locked() or bool(caption_requests), capabilities=["history_delete", "history_pagination", "global_en", "local_caption_ai", "caption_persistence", "watermark", "kids_studio", "kids_pipeline", "clip_exports", "smooth_crop", "source_quality", "wide_crop"])

@app.get("/favicon.ico")
def favicon(): return redirect("/static/favicon.svg", code=302)

@app.get("/")
def index(): return render_template("index.html", global_mode=False, kids_mode=False)

@app.get("/global")
def global_studio(): return render_template("index.html", global_mode=True, kids_mode=False, ideas=IDEAS, sources=SOURCES)

@app.get("/api/global/ideas")
def global_ideas(): return jsonify(ideas=IDEAS, sources=SOURCES, kind="editorial", updated="2026-11-04")

@app.get("/kids")
def kids_studio():
    return render_template(
        "index.html",
        global_mode=False,
        kids_mode=True,
        ideas=kids_content.IDEAS,
        categories=kids_content.CATEGORIES,
        sources=kids_content.SOURCES,
    )

@app.get("/kids/source")
def kids_source():
    brief_id = request.args.get("brief", "")
    if not kids_content.is_valid_brief_id(brief_id):
        return "Pilih brief tersimpan dari Studio Anak terlebih dahulu.", 400
    with lock:
        brief = kids_content.read_brief(KIDS_BRIEFS, brief_id)
    if not brief:
        return "Brief tidak ditemukan. Kembali ke Studio Anak.", 404
    return render_template("index.html", global_mode=False, kids_mode=False, kids_source=True, selected_brief=brief)

@app.get("/api/kids/ideas")
def kids_ideas():
    category = request.args.get("category", "").strip().lower()
    ideas = kids_content.IDEAS
    if category and category in kids_content.CATEGORIES:
        ideas = [i for i in ideas if i.get("category") == category]
    return jsonify(
        ideas=ideas,
        categories=kids_content.CATEGORIES,
        sources=kids_content.SOURCES,
        kind="editorial",
        target="3–5 tahun · Bahasa Indonesia",
        updated="2026-11-05"
    )

@app.get("/api/kids/briefs")
def get_kids_briefs():
    try:
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 10))
        if page < 1 or not 1 <= page_size <= 50:
            raise ValueError()
    except ValueError:
        return jsonify(error="Parameter halaman tidak valid."), 400
    category = request.args.get("category", "").strip().lower() or None
    if category and category not in kids_content.CATEGORIES:
        category = None
    with lock:
        result = kids_content.list_briefs(KIDS_BRIEFS, page=page, page_size=page_size, category=category)
    return jsonify(result), 200

@app.before_request
def limit_kids_brief_request():
    if request.path.startswith("/api/kids/briefs") and request.method in ("POST", "PATCH"):
        request.max_content_length = 32 * 1024

@app.post("/api/kids/briefs")
def create_kids_brief():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Body request harus berupa JSON."), 400
    try:
        validated = kids_content.validate_brief_payload(data, is_patch=False)
    except kids_content.KidsBriefError as exc:
        return jsonify(error=exc.message), exc.status_code

    brief_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    brief = {
        "brief_id": brief_id,
        "revision": 1,
        "idea_id": validated.get("idea_id"),
        "category": validated.get("category"),
        "age_band": validated["age_band"],
        "language": validated["language"],
        "title": validated["title"],
        "learning_goal": validated["learning_goal"],
        "outline": validated["outline"],
        "asset_notes": validated["asset_notes"],
        "target_duration": validated["target_duration"],
        "created_at": now,
        "updated_at": now,
    }
    with lock:
        try:
            kids_content.save_brief_atomic(KIDS_BRIEFS, brief)
        except OSError:
            return jsonify(error="Gagal menyimpan brief ke disk."), 500
    return jsonify(brief=brief), 201

@app.get("/api/kids/briefs/<brief_id>")
def get_kids_brief(brief_id):
    if not kids_content.is_valid_brief_id(brief_id):
        return jsonify(error="ID brief tidak valid."), 400
    with lock:
        brief = kids_content.read_brief(KIDS_BRIEFS, brief_id)
    if brief is None:
        return jsonify(error="Brief tidak ditemukan."), 404
    return jsonify(brief=brief), 200

@app.patch("/api/kids/briefs/<brief_id>")
def update_kids_brief(brief_id):
    if not kids_content.is_valid_brief_id(brief_id):
        return jsonify(error="ID brief tidak valid."), 400
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Body request harus berupa JSON."), 400

    expected_revision = data.get("expected_revision")
    if type(expected_revision) is not int or expected_revision < 1:
        return jsonify(error="Field 'expected_revision' wajib berupa integer positif."), 400

    try:
        validated = kids_content.validate_brief_payload(data, is_patch=True)
    except kids_content.KidsBriefError as exc:
        return jsonify(error=exc.message), exc.status_code

    with lock:
        current_brief = kids_content.read_brief(KIDS_BRIEFS, brief_id)
        if current_brief is None:
            return jsonify(error="Brief tidak ditemukan."), 404

        if current_brief.get("revision", 1) != expected_revision:
            return jsonify(
                error="Konflik revisi brief. Versi server telah diperbarui oleh sesi lain.",
                conflict=True,
                current_revision=current_brief.get("revision", 1),
                server_brief=current_brief,
            ), 409

        new_brief = copy.deepcopy(current_brief)
        for key, val in validated.items():
            new_brief[key] = val
        new_brief["revision"] = current_brief.get("revision", 1) + 1
        new_brief["updated_at"] = datetime.now(timezone.utc).isoformat()

        try:
            kids_content.save_brief_atomic(KIDS_BRIEFS, new_brief)
        except OSError:
            return jsonify(error="Gagal memperbarui brief ke disk."), 500

    return jsonify(brief=new_brief), 200

@app.delete("/api/kids/briefs/<brief_id>")
def delete_kids_brief(brief_id):
    if not kids_content.is_valid_brief_id(brief_id):
        return jsonify(error="ID brief tidak valid."), 400
    with lock:
        brief = kids_content.read_brief(KIDS_BRIEFS, brief_id)
        if brief is None:
            return jsonify(error="Brief tidak ditemukan."), 404
        deleted = kids_content.delete_brief(KIDS_BRIEFS, brief_id)
    if not deleted:
        return jsonify(error="Gagal menghapus brief."), 500
    return jsonify(brief_id=brief_id, deleted=True), 200

@app.get("/api/kids/briefs/<brief_id>/export")
def export_kids_brief(brief_id):
    if not kids_content.is_valid_brief_id(brief_id):
        return jsonify(error="ID brief tidak valid."), 400
    fmt = request.args.get("format", "txt").strip().lower()
    with lock:
        brief = kids_content.read_brief(KIDS_BRIEFS, brief_id)
    if brief is None:
        return jsonify(error="Brief tidak ditemukan."), 404

    if fmt == "json":
        response = Response(
            json.dumps(brief, ensure_ascii=False, indent=2),
            status=200,
            mimetype="application/json"
        )
        response.headers["Content-Disposition"] = f'attachment; filename="brief-{brief_id}.json"'
        return response
    else:
        text_content = kids_content.format_brief_txt(brief)
        response = Response(
            text_content,
            status=200,
            mimetype="text/plain; charset=utf-8"
        )
        response.headers["Content-Disposition"] = f'attachment; filename="brief-{brief_id}.txt"'
        return response

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
        resolution=request.form.get("resolution", "720")
        framing_layout=request.form.get("framing_layout", "full")
        if framing_layout not in ("full", "wide"): raise ValueError()
        source_quality=request.form.get("source_quality", "1080")
        if source_quality not in SOURCE_HEIGHTS: raise ValueError()
        if resolution not in RESOLUTIONS: raise ValueError()
        subtitle_style=request.form.get("subtitle_style", "classic")
        if subtitle_style not in SUBTITLE_STYLES: raise ValueError()
        lang=request.form.get("language","auto")
        if lang not in ("auto","id","en"): raise ValueError()
        audience=request.form.get("audience", "local")
        topic=request.form.get("topic", "general")
        if audience not in ("local", "global_en") or topic not in TOPICS: raise ValueError()
        if audience == "local": topic = "general"
    except ValueError: return jsonify(error="Pengaturan tidak valid."),400
    content_profile = request.form.get("content_profile", "general")
    kids_metadata = None
    if content_profile not in ("general", "kids"):
        return jsonify(error="Profil konten tidak valid."), 400
    if content_profile == "kids":
        if audience != "local" or lang != "id":
            return jsonify(error="Studio Anak hanya mendukung audience lokal dan bahasa Indonesia (id)."), 400
        if request.form.get("source_kind", "speech") != "speech":
            return jsonify(error="Lagu/gerak tanpa narasi jelas belum didukung clipper. Gunakan brief sebagai rencana dan sumber dengan ucapan jelas."), 400
        brief_id = request.form.get("brief_id", "")
        if not kids_content.is_valid_brief_id(brief_id):
            return jsonify(error="Pilih brief Studio Anak yang sudah disimpan."), 400
        with lock:
            brief = kids_content.read_brief(KIDS_BRIEFS, brief_id)
            if brief is None:
                return jsonify(error="Brief tidak ditemukan. Pilih ulang brief."), 404
            if request.form.get("brief_revision") != str(brief["revision"]):
                return jsonify(error="Brief berubah di sesi lain. Muat ulang brief sebelum membuat klip."), 409
            kids_metadata = {"age_band":"3_5", "language":"id", "brief_id":brief_id,
                             "brief_snapshot":copy.deepcopy(brief)}
    with lock:
        if active_export is not None or caption_requests or inference_lock.locked(): return jsonify(error="Ekspor atau AI lokal sedang berjalan. Tunggu sampai selesai."),409
        if any(not j.get("done") for j in jobs.values()): return jsonify(error="Ada video sedang diproses. Tunggu sampai selesai."),409
        jid=uuid.uuid4().hex
        folder=DATA/jid;folder.mkdir()
        now = datetime.now(timezone.utc).isoformat()
        original_name = Path(upload.filename.replace(chr(92), "/")).name if upload and upload.filename else None
        jobs[jid]=dict(id=jid, schema_version=2, title="Video YouTube" if url else original_name,
                       source_url=url or None, source_name=original_name if not url else None,
                       content_profile=content_profile, kids_metadata=kids_metadata,
                       source_quality=source_quality, framing_layout=framing_layout,
                       duration=duration, count=count, language=lang, resolution=resolution, audience=audience, topic=topic, subtitle_style=subtitle_style,
                       created_at=now, updated_at=now,
                       status="Dalam antrean…",progress=0,done=False,clips=[])
        save_job(jid)
    local=None
    if not url:
        local=folder/"source.mp4"
        try: upload.save(local)
        except Exception:
            update(jid,done=True,status="Gagal",error="File tidak dapat disimpan. Periksa ruang disk.")
            return jsonify(error="File tidak dapat disimpan. Periksa ruang disk."),400
    threading.Thread(target=process,args=(jid,url,local,duration,count,lang,resolution,audience,topic),kwargs={"subtitle_style":subtitle_style,"source_quality":source_quality,"framing_layout":framing_layout},daemon=True).start()
    return jsonify(id=jid),202

def job_summary(folder):
    if not re.fullmatch(r"[a-f0-9]{32}", folder.name) or folder.is_symlink():
        return None
    try:
        stat = (folder / "job.json").stat()
    except OSError:
        return None
    cache_key = str(folder.resolve())
    signature = (stat.st_mtime_ns, stat.st_size)
    with lock:
        cached = history_cache.get(cache_key)
        if cached and cached[0] == signature:
            history_cache.move_to_end(cache_key)
            return copy.deepcopy(cached[1])
    job = read_job(folder.name)
    if job is None:
        return None
    summary = {key: job.get(key) for key in (
        "id", "title", "created_at", "updated_at", "status", "progress", "done",
        "source_url", "source_name", "source_quality", "source_media", "framing_layout", "content_profile", "kids_metadata", "duration", "count", "language", "resolution", "audience", "topic", "subtitle_style", "error")}
    summary.pop("kids_metadata", None)
    summary["clip_count"] = len(job.get("clips", []))
    with lock:
        history_cache[cache_key] = (signature, copy.deepcopy(summary))
        history_cache.move_to_end(cache_key)
        while len(history_cache) > 1024:
            history_cache.popitem(last=False)
    return summary


@app.get("/api/jobs")
def history():
    try:
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 10))
        if page < 1 or not 1 <= page_size <= 50:
            raise ValueError()
    except ValueError:
        return jsonify(error="Parameter halaman tidak valid."), 400
    state = request.args.get("status", "all")
    if state not in ("all", "processing", "done", "failed"):
        return jsonify(error="Filter status tidak valid."), 400
    query = request.args.get("q", "").strip().casefold()[:200]
    summaries = [summary for folder in DATA.iterdir() if (summary := job_summary(folder)) is not None]
    summaries.sort(key=lambda job: (job["created_at"], job["id"]), reverse=True)
    total = len(summaries)
    def matches(job):
        category = "processing" if not job.get("done") else "failed" if job.get("error") else "done"
        text = " ".join(str(job.get(key) or "") for key in ("title", "source_url", "source_name")).casefold()
        return (state == "all" or category == state) and (not query or query in text)
    filtered = [job for job in summaries if matches(job)]
    pages = max(1, math.ceil(len(filtered) / page_size))
    page = min(page, pages)
    with lock:
        active_id = next((jid for jid, job in jobs.items() if not job.get("done")), None)
    offset = (page - 1) * page_size
    return jsonify(jobs=filtered[offset:offset+page_size], total=total, filtered_total=len(filtered),
                   page=page, page_size=page_size, total_pages=pages, active_job_id=active_id)


@app.get("/api/jobs/<jid>")
def status(jid):
    job = read_job(jid)
    return (jsonify(job),200) if job else (jsonify(error="Proses tidak ditemukan."),404)

@app.patch("/api/jobs/<jid>/clips/<clip_ref>/caption")
def update_caption(jid, clip_ref):
    if not re.fullmatch(r"[a-f0-9]{32}", jid):
        return jsonify(error="Riwayat tidak ditemukan."), 404
    if not request.is_json:
        return jsonify(error="Payload harus berupa JSON."), 400
    try:
        data = request.get_json(silent=False)
    except Exception:
        return jsonify(error="JSON tidak valid."), 400
    if not isinstance(data, dict):
        return jsonify(error="Payload harus berupa objek JSON."), 400
    if "caption" not in data:
        return jsonify(error="Field caption wajib diisi."), 400
    caption = data["caption"]
    if not isinstance(caption, str):
        return jsonify(error="Caption harus berupa teks."), 400
    if len(caption) > 2000:
        return jsonify(error="Caption melebihi batas 2.000 karakter."), 400
    if "expected_revision" not in data:
        return jsonify(error="Field expected_revision wajib diisi."), 400
    expected_revision = data["expected_revision"]
    if not isinstance(expected_revision, int) or isinstance(expected_revision, bool) or expected_revision < 1:
        return jsonify(error="expected_revision harus berupa integer positif."), 400

    job = read_job(jid)
    if job is None:
        return jsonify(error="Riwayat tidak ditemukan."), 404

    folder = DATA / jid
    with lock:
        if folder.is_symlink() or not folder.is_dir():
            return jsonify(error="Riwayat tidak ditemukan."), 404
        current = jobs.get(jid, job)
        ensure_clip_ids(current)

        target_clip = None
        target_index = None
        for idx, c in enumerate(current.get("clips", [])):
            if c.get("clip_id") == clip_ref:
                target_clip = c
                target_index = idx
                break
        if target_clip is None and clip_ref.isdigit():
            idx = int(clip_ref)
            if 0 <= idx < len(current.get("clips", [])):
                target_clip = current["clips"][idx]
                target_index = idx
        if target_clip is None:
            return jsonify(error="Klip tidak ditemukan."), 404

        current_rev = target_clip.get("caption_revision", target_clip.get("metadata_revision", 1))
        if expected_revision != current_rev:
            return jsonify(
                error="Konflik revisi caption. Versi server telah diperbarui.",
                conflict=True,
                current_revision=current_rev,
                server_caption=target_clip.get("caption", ""),
                server_source=target_clip.get("caption_source", "none"),
                server_updated_at=target_clip.get("caption_updated_at")
            ), 409

        # Transactional copy-on-write commit
        updated_job = copy.deepcopy(current)
        updated_clip = updated_job["clips"][target_index]
        now = datetime.now(timezone.utc).isoformat()
        new_rev = current_rev + 1
        updated_clip["caption"] = caption
        updated_clip["caption_source"] = "manual"
        updated_clip["caption_language"] = "unverified"
        updated_clip["caption_updated_at"] = now
        updated_clip["caption_revision"] = new_rev
        updated_clip["metadata_revision"] = new_rev
        updated_clip["caption_note"] = "Edit manual · tersimpan"
        updated_clip["caption_status"] = "ready"
        updated_job["updated_at"] = now
        updated_job["schema_version"] = 2

        try:
            write_job_atomic(jid, updated_job)
        except OSError as exc:
            return jsonify(error="Gagal menyimpan ke disk: " + str(exc)), 500

        jobs[jid] = updated_job
        history_cache.pop(str(folder.resolve()), None)

        return jsonify(
            clip_id=updated_clip["clip_id"],
            caption=updated_clip["caption"],
            caption_source=updated_clip["caption_source"],
            caption_language=updated_clip["caption_language"],
            caption_updated_at=updated_clip["caption_updated_at"],
            metadata_revision=updated_clip["metadata_revision"],
            caption_revision=updated_clip["caption_revision"],
            caption_note=updated_clip["caption_note"]
        ), 200


def _handle_generate_caption(jid, clip_ref):
    global caption_requests
    if not re.fullmatch(r"[a-f0-9]{32}", jid):
        return jsonify(error="Riwayat tidak ditemukan."), 404
    job = read_job(jid)
    if not job:
        return jsonify(error="Riwayat tidak ditemukan."), 404
    ensure_clip_ids(job)

    target_clip = None
    target_index = None
    for idx, c in enumerate(job.get("clips", [])):
        if c.get("clip_id") == clip_ref or str(idx) == str(clip_ref):
            target_clip = c
            target_index = idx
            break
    if target_clip is None and isinstance(clip_ref, int) and 0 <= clip_ref < len(job.get("clips", [])):
        target_clip = job["clips"][clip_ref]
        target_index = clip_ref
    if target_clip is None:
        return jsonify(error="Klip tidak ditemukan."), 404

    target_clip_id = target_clip["clip_id"]
    initial_revision = target_clip.get("caption_revision", target_clip.get("metadata_revision", 1))

    expected_revision = None
    if request.is_json:
        try:
            req_data = request.get_json(silent=True)
            if isinstance(req_data, dict) and "expected_revision" in req_data:
                exp_rev = req_data["expected_revision"]
                if not isinstance(exp_rev, int) or isinstance(exp_rev, bool) or exp_rev < 1:
                    return jsonify(error="expected_revision harus berupa integer positif."), 400
                expected_revision = exp_rev
        except Exception:
            pass

    if expected_revision is not None and expected_revision != initial_revision:
        return jsonify(
            error="Konflik revisi caption. Versi server telah diperbarui.",
            conflict=True,
            current_revision=initial_revision,
            current_caption=target_clip.get("caption", ""),
            caption_source=target_clip.get("caption_source", "none")
        ), 409

    with lock:
        if active_export is not None or any(not item.get("done") for item in jobs.values()):
            return jsonify(error="Tunggu pemrosesan video/ekspor selesai sebelum membuat caption AI."), 409
        caption_requests += 1

    try:
        result = summarize(target_clip.get("text", ""), job.get("audience", "local"))
        if job.get("content_profile") == "kids":
            result = kids_caption(result)
    except UnclearTranscript as exc:
        return jsonify(error=str(exc), caption_status="needs_review"), 422
    except CaptionUnavailable as exc:
        return jsonify(error=str(exc), caption_status="unavailable"), 503
    finally:
        with lock:
            caption_requests -= 1

    with lock:
        folder = DATA / jid
        if not folder.is_dir() or folder.is_symlink():
            return jsonify(error="Riwayat telah dihapus."), 404
        current = jobs.get(jid, job)
        ensure_clip_ids(current)

        current_clip = None
        current_index = None
        for idx, c in enumerate(current.get("clips", [])):
            if c.get("clip_id") == target_clip_id:
                current_clip = c
                current_index = idx
                break
        if current_clip is None and target_index is not None and 0 <= target_index < len(current.get("clips", [])):
            current_clip = current["clips"][target_index]
            current_index = target_index
        if current_clip is None:
            return jsonify(error="Klip tidak ditemukan."), 404

        current_cap_rev = current_clip.get("caption_revision", current_clip.get("metadata_revision", 1))
        if current_cap_rev != initial_revision:
            msg = "Caption telah diperbarui secara manual saat AI sedang merangkum. Edit manual dipertahankan." if current_clip.get("caption_source") == "manual" else "Caption telah diperbarui saat AI sedang merangkum. Perubahan terbaru dipertahankan."
            return jsonify(
                error=msg,
                conflict=True,
                current_revision=current_cap_rev,
                current_caption=current_clip.get("caption", ""),
                caption_source=current_clip.get("caption_source", "manual")
            ), 409

        updated_job = copy.deepcopy(current)
        target_to_update = updated_job["clips"][current_index]
        now = datetime.now(timezone.utc).isoformat()
        target_to_update.update(result)
        target_to_update["caption_source"] = "ai_local"
        target_to_update["caption_updated_at"] = now
        new_rev = current_cap_rev + 1
        target_to_update["caption_revision"] = new_rev
        target_to_update["metadata_revision"] = new_rev
        updated_job["updated_at"] = now
        updated_job["schema_version"] = 2

        try:
            write_job_atomic(jid, updated_job)
        except OSError as exc:
            return jsonify(error="Gagal menyimpan ke disk: " + str(exc)), 500

        jobs[jid] = updated_job
        history_cache.pop(str(folder.resolve()), None)

    return jsonify({
        **result,
        "clip_id": target_to_update["clip_id"],
        "metadata_revision": target_to_update["metadata_revision"],
        "caption_updated_at": target_to_update["caption_updated_at"]
    })


@app.post("/api/jobs/<jid>/clips/<int:index>/caption")
def generate_caption(jid, index):
    return _handle_generate_caption(jid, index)


@app.post("/api/jobs/<jid>/clips/<clip_ref>/caption")
def generate_caption_ref(jid, clip_ref):
    return _handle_generate_caption(jid, clip_ref)


@app.patch("/api/jobs/<jid>/clips/<clip_ref>/watermark")
def update_watermark(jid, clip_ref):
    if not re.fullmatch(r"[a-f0-9]{32}", jid):
        return jsonify(error="Riwayat tidak ditemukan."), 404
    job = read_job(jid)
    if not job:
        return jsonify(error="Riwayat tidak ditemukan."), 404
    folder = DATA / jid

    data = request.get_json(silent=True) or {}
    if "watermark" not in data:
        return jsonify(error="Field 'watermark' wajib diisi."), 400

    expected_revision = data.get("expected_revision")
    if expected_revision is not None:
        try:
            expected_revision = int(expected_revision)
        except (ValueError, TypeError):
            return jsonify(error="expected_revision harus berupa angka bulat."), 400

    try:
        validated_config = watermark.validate_watermark_config(data["watermark"], WATERMARK_ASSETS)
    except watermark.WatermarkError as exc:
        return jsonify(error=str(exc)), 400

    with lock:
        current = jobs.get(jid, job)
        ensure_clip_ids(current)

        target_clip = None
        target_index = None
        for idx, c in enumerate(current.get("clips", [])):
            if c.get("clip_id") == clip_ref:
                target_clip = c
                target_index = idx
                break
        if target_clip is None and clip_ref.isdigit():
            idx = int(clip_ref)
            if 0 <= idx < len(current.get("clips", [])):
                target_clip = current["clips"][idx]
                target_index = idx
        if target_clip is None:
            return jsonify(error="Klip tidak ditemukan."), 404

        current_rev = target_clip.get("watermark_revision", 1)
        if expected_revision is not None and expected_revision != current_rev:
            return jsonify(
                error="Konflik revisi watermark. Versi server telah diperbarui.",
                conflict=True,
                current_revision=current_rev,
                server_watermark=target_clip.get("watermark"),
                server_updated_at=target_clip.get("watermark_updated_at")
            ), 409

        # Transactional copy-on-write commit
        updated_job = copy.deepcopy(current)
        updated_clip = updated_job["clips"][target_index]
        now = datetime.now(timezone.utc).isoformat()
        new_rev = current_rev + 1
        updated_clip["watermark"] = validated_config
        updated_clip["watermark_updated_at"] = now
        updated_clip["watermark_revision"] = new_rev
        updated_job["updated_at"] = now
        updated_job["schema_version"] = 2

        try:
            write_job_atomic(jid, updated_job)
        except OSError as exc:
            return jsonify(error="Gagal menyimpan ke disk: " + str(exc)), 500

        jobs[jid] = updated_job
        history_cache.pop(str(folder.resolve()), None)

        clash, clash_msg = watermark.detect_subtitle_clash(
            validated_config,
            canvas_w=720,
            canvas_h=1280,
            asset_w=validated_config.get("asset_width"),
            asset_h=validated_config.get("asset_height")
        )

        return jsonify(
            clip_id=updated_clip["clip_id"],
            watermark=updated_clip["watermark"],
            watermark_revision=updated_clip["watermark_revision"],
            metadata_revision=updated_clip.get("metadata_revision", 1),
            clash_detected=clash,
            clash_message=clash_msg,
            watermark_updated_at=updated_clip["watermark_updated_at"]
        ), 200


@app.post("/api/watermark-assets")
def upload_watermark_asset():
    file = request.files.get("file") or request.files.get("logo")
    if not file or not file.filename:
        return jsonify(error="File logo harus diunggah."), 400

    try:
        file_bytes = file.read()
    except Exception as exc:
        return jsonify(error="Gagal membaca file unggahan: " + str(exc)), 400

    try:
        asset_info = watermark.validate_and_save_logo(file_bytes, WATERMARK_ASSETS)
    except watermark.PayloadTooLargeError as exc:
        return jsonify(error=str(exc)), 413
    except watermark.WatermarkError as exc:
        return jsonify(error=str(exc)), 400
    except Exception as exc:
        return jsonify(error="Gagal memproses gambar logo: " + str(exc)), 400

    return jsonify(asset_info), 201


@app.get("/api/watermark-assets/<asset_id>/preview")
def preview_watermark_asset(asset_id):
    if not re.fullmatch(r"[a-f0-9]{16,64}", asset_id):
        return jsonify(error="ID aset tidak valid."), 404

    png_file = WATERMARK_ASSETS / f"{asset_id}.png"
    jpg_file = WATERMARK_ASSETS / f"{asset_id}.jpg"

    if png_file.exists():
        return send_from_directory(WATERMARK_ASSETS, f"{asset_id}.png", mimetype="image/png")
    elif jpg_file.exists():
        return send_from_directory(WATERMARK_ASSETS, f"{asset_id}.jpg", mimetype="image/jpeg")
    else:
        return jsonify(error="Aset logo tidak ditemukan."), 404


@app.get("/api/watermark-presets")
def get_watermark_presets():
    with lock:
        presets = watermark.load_presets(WATERMARK_PRESETS)
    return jsonify(presets=presets), 200


@app.post("/api/watermark-presets")
def create_watermark_preset():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    if not name or len(name) > watermark.MAX_PRESET_NAME_LENGTH:
        return jsonify(error=f"Nama preset harus diisi (maksimal {watermark.MAX_PRESET_NAME_LENGTH} karakter)."), 400

    try:
        config = watermark.validate_watermark_config(data.get("configuration", {}), WATERMARK_ASSETS)
    except watermark.WatermarkError as exc:
        return jsonify(error=str(exc)), 400

    preset_id = uuid.uuid4().hex[:16]
    now = datetime.now(timezone.utc).isoformat()
    new_preset = {
        "preset_id": preset_id,
        "revision": 1,
        "name": name,
        "configuration": config,
        "created_at": now,
        "updated_at": now
    }

    with lock:
        presets = watermark.load_presets(WATERMARK_PRESETS)
        presets.append(new_preset)
        try:
            watermark.save_presets_atomic(WATERMARK_PRESETS, presets)
        except OSError as exc:
            return jsonify(error="Gagal menyimpan preset ke disk: " + str(exc)), 500

    return jsonify(new_preset), 201


@app.patch("/api/watermark-presets/<preset_id>")
def update_watermark_preset(preset_id):
    if not re.fullmatch(r"[a-f0-9]{16,64}", preset_id):
        return jsonify(error="ID preset tidak valid."), 404

    data = request.get_json(silent=True) or {}
    expected_revision = data.get("expected_revision")
    if expected_revision is not None:
        try:
            expected_revision = int(expected_revision)
        except (ValueError, TypeError):
            return jsonify(error="expected_revision harus berupa angka bulat."), 400

    with lock:
        presets = watermark.load_presets(WATERMARK_PRESETS)
        target_preset = None
        for p in presets:
            if p.get("preset_id") == preset_id:
                target_preset = p
                break
        if not target_preset:
            return jsonify(error="Preset tidak ditemukan."), 404

        current_rev = target_preset.get("revision", 1)
        if expected_revision is not None and expected_revision != current_rev:
            return jsonify(
                error="Konflik revisi: Preset telah diperbarui di sesi lain.",
                conflict=True,
                current_revision=current_rev
            ), 409

        if "name" in data:
            new_name = str(data["name"]).strip()
            if not new_name or len(new_name) > watermark.MAX_PRESET_NAME_LENGTH:
                return jsonify(error=f"Nama preset harus diisi (maksimal {watermark.MAX_PRESET_NAME_LENGTH} karakter)."), 400
            target_preset["name"] = new_name

        if "configuration" in data:
            try:
                new_config = watermark.validate_watermark_config(data["configuration"], WATERMARK_ASSETS)
            except watermark.WatermarkError as exc:
                return jsonify(error=str(exc)), 400
            target_preset["configuration"] = new_config

        target_preset["revision"] = current_rev + 1
        target_preset["updated_at"] = datetime.now(timezone.utc).isoformat()

        try:
            watermark.save_presets_atomic(WATERMARK_PRESETS, presets)
        except OSError as exc:
            return jsonify(error="Gagal menyimpan preset ke disk: " + str(exc)), 500

    return jsonify(target_preset), 200


def find_clip(job, clip_ref):
    return next((c for i, c in enumerate(job.get("clips", []))
                 if c.get("clip_id") == clip_ref or str(i) == str(clip_ref)), None)


def commit_export(jid, clip_id, record):
    # Caller holds app lock. Never publish metadata before atomic disk write.
    current = jobs.get(jid) or read_job(jid)
    if not current:
        raise ValueError("Riwayat tidak tersedia.")
    updated = copy.deepcopy(current)
    clip = find_clip(updated, clip_id)
    if clip is None:
        raise ValueError("Klip tidak tersedia.")
    clip.setdefault("exports", {})[record["export_id"]] = record
    write_job_atomic(jid, updated)
    jobs[jid] = updated
    history_cache.pop(str((DATA / jid).resolve()), None)


def export_worker(jid, clip_id, record, source):
    global active_export
    folder = DATA / jid / "exports" / record["export_id"]
    destination = folder / record["filename"]
    try:
        folder.mkdir(parents=True, exist_ok=False)
        config = copy.deepcopy(record["settings"]["watermark"])
        clip_exports.render_export(FFMPEG, source, destination, config, WATERMARK_ASSETS,
                                   kind=record["kind"], frame_time=record["settings"]["frame_time"],
                                   ratio=record["settings"]["ratio"])
        record.update(status="done", finished_at=datetime.now(timezone.utc).isoformat())
        with lock:
            commit_export(jid, clip_id, record)
    except Exception as exc:
        destination.unlink(missing_ok=True)
        record.update(status="failed", error=str(exc), finished_at=datetime.now(timezone.utc).isoformat())
        try:
            with lock:
                commit_export(jid, clip_id, record)
        except Exception:
            pass  # GET marks an abandoned running record interrupted once the reservation ends.
    finally:
        with lock:
            active_export = None


@app.post("/api/jobs/<jid>/clips/<clip_ref>/exports")
def create_clip_export(jid, clip_ref):
    global active_export
    if not re.fullmatch(r"[a-f0-9]{32}", jid):
        return jsonify(error="Riwayat tidak ditemukan."), 404
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Payload harus JSON object."), 400
    export_id = data.get("request_id", "")
    if not isinstance(export_id, str) or not re.fullmatch(r"[a-f0-9]{32}", export_id):
        return jsonify(error="request_id harus ID heksadesimal 32 karakter."), 400
    kind = data.get("kind")
    ratio = data.get("ratio", "vertical")
    frame_time = data.get("frame_time", 0)
    revision = data.get("expected_watermark_revision")
    if kind not in ("video", "thumbnail") or ratio not in ("vertical", "landscape"):
        return jsonify(error="Jenis ekspor atau rasio tidak valid."), 400
    if type(frame_time) not in (int, float) or not math.isfinite(frame_time) or frame_time < 0:
        return jsonify(error="Waktu frame harus angka positif atau nol."), 400
    if type(revision) is not int or revision < 1:
        return jsonify(error="Revisi watermark wajib integer positif."), 400
    with lock:
        if (DATA / jid).is_symlink() or (DATA / jid / "exports").is_symlink():
            return jsonify(error="Riwayat tidak tersedia."), 404
        job = read_job(jid)
        if not job:
            return jsonify(error="Riwayat tidak ditemukan."), 404
        clip = find_clip(job, clip_ref)
        if not clip:
            return jsonify(error="Klip tidak ditemukan."), 404
        previous = clip.get("exports", {}).get(export_id)
        intent = {"kind":kind, "ratio":ratio, "frame_time":frame_time, "watermark_revision":revision}
        if previous:
            if previous.get("intent") != intent:
                return jsonify(error="request_id sudah dipakai untuk pengaturan lain."), 409
            return jsonify(export=previous), 200
        if active_export or caption_requests or inference_lock.locked() or any(not j.get("done") for j in jobs.values()) or not job.get("done"):
            return jsonify(error="Ada pemrosesan aktif. Tunggu selesai sebelum mengekspor."), 409
        if revision != clip.get("watermark_revision", 1):
            return jsonify(error="Draft watermark berubah. Muat ulang hasil sebelum ekspor."), 409
        if not re.fullmatch(r"clip-[1-5]\.mp4", clip.get("file", "")):
            return jsonify(error="File klip tidak tersedia."), 404
        source = DATA / jid / clip["file"]
        if source.is_symlink() or not source.is_file():
            return jsonify(error="File klip tidak tersedia."), 404
        try:
            config = watermark.validate_watermark_config(clip.get("watermark", {}), WATERMARK_ASSETS)
        except watermark.WatermarkError as exc:
            return jsonify(error=str(exc)), 400
        if kind == "video" and not config["enabled"]:
            return jsonify(error="Aktifkan dan simpan watermark terlebih dahulu."), 400
        record = {"export_id":export_id, "kind":kind, "status":"running", "intent":intent,
                  "filename":"video.mp4" if kind == "video" else "thumbnail.png",
                  "created_at":datetime.now(timezone.utc).isoformat(),
                  "settings":{"watermark":copy.deepcopy(config), "watermark_revision":revision,
                              "source_file":clip["file"], "ratio":ratio, "frame_time":frame_time}}
        try:
            commit_export(jid, clip["clip_id"], record)
        except OSError:
            return jsonify(error="Gagal menyimpan antrean ekspor."), 500
        active_export = (jid, clip["clip_id"], export_id)
        worker = threading.Thread(target=export_worker, args=(jid, clip["clip_id"], copy.deepcopy(record), source), daemon=True)
        try:
            worker.start()
        except Exception as exc:
            active_export = None
            record.update(status="failed", error=str(exc))
            commit_export(jid, clip["clip_id"], record)
            return jsonify(error="Worker ekspor tidak dapat dimulai."), 500
    return jsonify(export=record), 202


@app.get("/api/jobs/<jid>/clips/<clip_ref>/exports/<export_id>")
@app.get("/api/jobs/<jid>/clips/<clip_ref>/exports/<export_id>/file")
def get_clip_export(jid, clip_ref, export_id):
    if not re.fullmatch(r"[a-f0-9]{32}", export_id) or not re.fullmatch(r"[a-f0-9]{32}", jid):
        return jsonify(error="Ekspor tidak ditemukan."), 404
    with lock:
        if (DATA / jid).is_symlink() or (DATA / jid / "exports").is_symlink():
            return jsonify(error="Riwayat tidak tersedia."), 404
        job = read_job(jid)
        clip = find_clip(job, clip_ref) if job else None
        record = copy.deepcopy(clip.get("exports", {}).get(export_id)) if clip else None
        if not record:
            return jsonify(error="Ekspor tidak ditemukan."), 404
        if record["status"] == "running" and active_export != (jid, clip["clip_id"], export_id):
            record.update(status="failed", error="Ekspor terputus. Buat ekspor baru; hasil lama tetap tersedia.")
    if request.path.endswith("/file"):
        if record["status"] != "done":
            return jsonify(error="Ekspor belum selesai."), 409
        folder = DATA / jid / "exports" / export_id
        if folder.is_symlink() or (folder / record["filename"]).is_symlink():
            return jsonify(error="Berkas tidak tersedia."), 404
        return send_from_directory(folder, record["filename"], as_attachment=request.args.get("download") == "1")
    return jsonify(export=record)


@app.delete("/api/jobs/<jid>")
def delete_job(jid):
    if not re.fullmatch(r"[a-f0-9]{32}", jid):
        return jsonify(error="Riwayat tidak ditemukan."), 404
    folder = DATA / jid
    with lock:
        if folder.is_symlink() or not folder.is_dir():
            return jsonify(error="Riwayat tidak ditemukan."), 404
        if (active_export and active_export[0] == jid) or (jid in jobs and not jobs[jid].get("done")):
            return jsonify(error="Video masih diproses. Tunggu sampai selesai sebelum menghapus."), 409
        try:
            shutil.rmtree(folder)
        except OSError:
            return jsonify(error="Berkas belum dapat dihapus. Periksa izin folder dan coba lagi."), 500
        jobs.pop(jid, None)
        history_cache.pop(str(folder.resolve()), None)
    return jsonify(id=jid, deleted=True)


@app.get("/files/<jid>/<name>")
def files(jid,name):
    if not re.fullmatch(r"[a-f0-9]{32}",jid) or not re.fullmatch(r"clip-[1-5]\.(mp4|ass)",name): return "Tidak ditemukan",404
    return send_from_directory(DATA/jid,name,as_attachment=request.args.get("download")=="1")

if __name__=="__main__":
    app.run(host="127.0.0.1",port=8765,debug=False)
