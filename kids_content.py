"""Katalog ide editorial dan pengelolaan brief untuk Studio Anak (3–5 tahun, Indonesia).

Berdasarkan riset docs/KIDS_CONTENT_RESEARCH.md dan PRD docs/prd/KLIP_KIDS_STUDIO.md.
Bukan feed tren live, proyeksi performa, atau analisis penonton individual.
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Dict, List, Optional, Tuple
import uuid

# Kategori terkurasi untuk konten anak usia 3–5 tahun
CATEGORIES: Dict[str, Dict[str, str]] = {
    "warna": {"label": "Warna", "description": "Pengenalan dan pembedaan warna dasar."},
    "hitung": {"label": "Hitung 1–5", "description": "Menghitung benda nyata jumlah kecil secara berurutan."},
    "bentuk": {"label": "Bentuk", "description": "Mengenali geometri sederhana dari benda sehari-hari."},
    "hewan": {"label": "Suara Hewan", "description": "Mencocokkan suara khas dengan wujud dan nama hewan."},
    "lagu": {"label": "Lagu & Rutinitas", "description": "Melodi orisinal pendek untuk rutinitas harian anak."},
    "gerak": {"label": "Gerak & Motorik", "description": "Meniru urutan gerak fisik sederhana (tepuk, lompat)."},
    "cerita": {"label": "Cerita & Giliran", "description": "Cerita karakter singkat tentang berbagi dan bergiliran."},
    "emosi": {"label": "Emosi Dasar", "description": "Mengenali ekspresi senang, sedih, dan meresponsnya."},
    "gambar": {"label": "Menggambar Bentuk", "description": "Menghubungkan bentuk dasar menjadi objek yang dikenal."},
    "ukuran": {"label": "Besar & Kecil", "description": "Membandingkan dua objek sejenis dengan ukuran berbeda."},
}

# 10 ide editorial orisinal dari riset
IDEAS: List[Dict[str, Any]] = [
    {
        "idea_id": "warna-01",
        "category": "warna",
        "age_band": "3_5",
        "language": "id",
        "title": "Mana Benda Merah?",
        "learning_goal": "Mengenali warna merah di antara benda sekitar",
        "outline": "Pembukaan: Salam ramah dan tunjukkan 3 benda berbeda warna di atas meja.\nKegiatan: Ajak anak mencari dan menunjuk benda yang berwarna merah.\nPenutup: Sebutkan kembali benda merah tersebut dan puji anak.",
        "suggested_duration": 30,
        "asset_notes": "3 benda nyata warna berbeda (misal apel merah, daun hijau, balok biru) disiapkan sendiri.",
        "workflow_fit": "cocok dicoba dengan clipper ucapan",
        "workflow_note": "Fokus pada percakapan/tanya-jawab langsung yang jelas terdengar.",
        "provenance": "editorial",
    },
    {
        "idea_id": "hitung-01",
        "category": "hitung",
        "age_band": "3_5",
        "language": "id",
        "title": "Hitung Lima Balok",
        "learning_goal": "Menghitung angka 1 sampai 5 berurutan",
        "outline": "Pembukaan: Perlihatkan balok yang masih berantakan.\nKegiatan: Letakkan balok satu per satu sambil menghitung jelas: satu, dua, tiga, empat, lima.\nPenutup: Tunjuk tumpukan balok dan tegaskan jumlahnya: ada lima balok!",
        "suggested_duration": 30,
        "asset_notes": "5 balok mainan kayu atau plastik aman dengan warna kontras.",
        "workflow_fit": "cocok dicoba dengan clipper ucapan",
        "workflow_note": "Beri jeda sejenak antar angka agar ucapan terdengar utuh oleh clipper.",
        "provenance": "editorial",
    },
    {
        "idea_id": "bentuk-01",
        "category": "bentuk",
        "age_band": "3_5",
        "language": "id",
        "title": "Cari Lingkarannya",
        "learning_goal": "Membedakan bentuk lingkaran dari persegi",
        "outline": "Pembukaan: Tunjukkan potongan karton lingkaran dan persegi.\nKegiatan: Jelaskan lingkaran yang bulat tanpa sudut, lalu minta anak memilih lingkaran.\nPenutup: Tunjukkan contoh lingkaran lain di sekitar (misal tutup toples atau bola).",
        "suggested_duration": 30,
        "asset_notes": "Potongan karton bentuk lingkaran dan persegi atau benda rumah tangga bulat.",
        "workflow_fit": "cocok dicoba dengan clipper ucapan",
        "workflow_note": "Pertahankan visual objek tetap di tengah kamera saat dijelaskan.",
        "provenance": "editorial",
    },
    {
        "idea_id": "hewan-01",
        "category": "hewan",
        "age_band": "3_5",
        "language": "id",
        "title": "Siapa yang Mengeong?",
        "learning_goal": "Mencocokkan suara mengeong dengan hewan kucing",
        "outline": "Pembukaan: Putar efek suara mengeong rekaman sendiri/berizin.\nKegiatan: Tanyakan hewan apa yang bersuara demikian, lalu tunjukkan gambar/boneka kucing.\nPenutup: Tirukan suara bersama dan sebut nama hewan: kucing!",
        "suggested_duration": 30,
        "asset_notes": "Efek suara kucing milik sendiri atau lisensi bebas, ditambah boneka/gambar kucing.",
        "workflow_fit": "cocok dicoba dengan clipper ucapan",
        "workflow_note": "Pastikan suara narator tidak tertimpa keras oleh efek suara latar.",
        "provenance": "editorial",
    },
    {
        "idea_id": "lagu-01",
        "category": "lagu",
        "age_band": "3_5",
        "language": "id",
        "title": "Lagu Rapikan Mainan",
        "learning_goal": "Mengenalkan kebiasaan merapikan mainan setelah bermain",
        "outline": "Pembukaan: Ajak anak menyanyi lagu pendek orisinal tentang merapikan mainan.\nKegiatan: Nyanyikan 2 baris melodi sambil memasukkan mainan ke dalam keranjang.\nPenutup: Tunjukkan ruangan yang sudah rapi dan ucapkan terima kasih.",
        "suggested_duration": 30,
        "asset_notes": "Melodi orisinal ciptaan sendiri, kotak mainan dan beberapa mainan aman.",
        "workflow_fit": "rencana produksi; perlu pemilihan manual",
        "workflow_note": "Lagu/gerak bukan janji automatic clipper mampu memilih lirik/ketukan/gerakan otomatis; gunakan trim manual setelah editor tersedia.",
        "provenance": "editorial",
        "source_url": "https://blog.youtube/culture-and-trends/baby-shark/",
        "verified_at": "2025-10-13",
    },
    {
        "idea_id": "gerak-01",
        "category": "gerak",
        "age_band": "3_5",
        "language": "id",
        "title": "Tepuk Tiga Kali",
        "learning_goal": "Meniru urutan ketukan gerak motorik sederhana",
        "outline": "Pembukaan: Angkat kedua tangan dan beri aba-aba siap.\nKegiatan: Beri contoh tepuk tangan tiga kali: prok, prok, prok! Beri jeda 2 detik bagi anak untuk meniru.\nPenutup: Tepuk bersama sekali lagi sebagai apresiasi.",
        "suggested_duration": 15,
        "asset_notes": "Gerakan tangan instruktur di kamera dengan pencahayaan jelas.",
        "workflow_fit": "rencana produksi; perlu pemilihan manual",
        "workflow_note": "Lagu/gerak bukan janji automatic clipper mampu memilih lirik/ketukan/gerakan otomatis; periksa jeda tepuk.",
        "provenance": "editorial",
    },
    {
        "idea_id": "cerita-01",
        "category": "cerita",
        "age_band": "3_5",
        "language": "id",
        "title": "Aku Mau Bergiliran",
        "learning_goal": "Mengenalkan konsep bergiliran dan sabar menunggu mainan",
        "outline": "Pembukaan: Dua boneka buatan sendiri (Kancil & Kelinci) ingin bermain ayunan.\nKegiatan: Kancil bermain dahulu 3 detik, lalu bergantian dengan Kelinci dengan gembira.\nPenutup: Kesimpulan ramah: bermain bergiliran itu menyenangkan dan adil.",
        "suggested_duration": 45,
        "asset_notes": "Dua boneka tangan buatan sendiri dan satu mainan ayunan kecil.",
        "workflow_fit": "cocok dicoba dengan clipper ucapan",
        "workflow_note": "Suara kedua karakter dibedakan intonasinya tetapi tetap jelas berbahasa Indonesia.",
        "provenance": "editorial",
    },
    {
        "idea_id": "emosi-01",
        "category": "emosi",
        "age_band": "3_5",
        "language": "id",
        "title": "Senang atau Sedih?",
        "learning_goal": "Mengenali perbedaan ekspresi wajah senang dan sedih",
        "outline": "Pembukaan: Tunjukkan wajah tersenyum lalu sebutkan: ini wajah senang.\nKegiatan: Tunjukkan wajah sedih (misal balon kempes), lalu tanyakan perasaannya.\nPenutup: Ajak tersenyum bersama dan beri pelukan ramah pada boneka.",
        "suggested_duration": 30,
        "asset_notes": "Kartu ekspresi wajah ilustrasi sendiri atau peragaan ekspresi oleh pendamping.",
        "workflow_fit": "cocok dicoba dengan clipper ucapan",
        "workflow_note": "Gunakan kata-kata sederhana yang menenangkan; hindari ekspresi yang menakutkan.",
        "provenance": "editorial",
    },
    {
        "idea_id": "gambar-01",
        "category": "gambar",
        "age_band": "3_5",
        "language": "id",
        "title": "Lingkaran Jadi Ikan",
        "learning_goal": "Menghubungkan bentuk geometri lingkaran menjadi gambar ikan sederhana",
        "outline": "Pembukaan: Gambar sebuah lingkaran besar di atas kertas putih.\nKegiatan: Tambahkan segitiga untuk ekor dan titik untuk mata perlahan-lahan.\nPenutup: Tunjukkan hasilnya: lingkaran berubah menjadi seekor ikan yang lucu!",
        "suggested_duration": 45,
        "asset_notes": "Kertas gambar putih, spidol warna gelap non-toksik, meja stabil.",
        "workflow_fit": "cocok dicoba dengan clipper ucapan",
        "workflow_note": "Gerakan tangan menggambar dilakukan perlahan agar anak dapat mengikuti langkahnya.",
        "provenance": "editorial",
    },
    {
        "idea_id": "ukuran-01",
        "category": "ukuran",
        "age_band": "3_5",
        "language": "id",
        "title": "Besar dan Kecil",
        "learning_goal": "Membandingkan dua objek sejenis dengan ukuran kontras",
        "outline": "Pembukaan: Letakkan dua bola plastik: satu bola besar dan satu bola kecil.\nKegiatan: Angkat bola besar lebih dulu sambil menyebut 'besar', lalu angkat bola kecil sambil menyebut 'kecil'.\nPenutup: Tanyakan pada anak: mana bola yang besar? Tunjuk jawabannya bersama.",
        "suggested_duration": 30,
        "asset_notes": "Dua bola plastik atau cangkir dengan warna sama tetapi ukuran jelas berbeda.",
        "workflow_fit": "cocok dicoba dengan clipper ucapan",
        "workflow_note": "Gunakan perbandingan yang kontras (minimal 2x lipat ukuran) agar terlihat jelas di layar ponsel vertikal.",
        "provenance": "editorial",
    },
]

# Sumber acuan platform dan kebijakan kualitas
SOURCES: List[Dict[str, str]] = [
    {
        "label": "YouTube: prinsip kualitas konten anak & keluarga",
        "url": "https://support.google.com/youtube/answer/10774223?hl=en",
        "note": "Menekankan konten ramah anak, edukatif, dan menghargai keberagaman.",
    },
    {
        "label": "YouTube: panduan penentuan audiens Made for Kids",
        "url": "https://support.google.com/youtube/answer/9527654?hl=en",
        "note": "Tanggung jawab kreator untuk menetapkan target penonton konten.",
    },
    {
        "label": "YouTube Culture & Trends: studi lagu anak Baby Shark (Juni 2025)",
        "url": "https://blog.youtube/culture-and-trends/baby-shark/",
        "note": "Bukti popularitas lagu repetitif sederhana (bukan proyeksi video baru).",
    },
]

# Batasan validasi brief
MAX_TITLE_LENGTH = 120
MAX_GOAL_LENGTH = 300
MAX_OUTLINE_LENGTH = 2000
MAX_ASSETS_LENGTH = 2000
ALLOWED_DURATIONS = (15, 30, 45, 60)
ALLOWED_AGE_BAND = "3_5"
ALLOWED_LANGUAGE = "id"


class KidsBriefError(Exception):
    """Kesalahan validasi atau penanganan brief anak."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class KidsBriefConflictError(KidsBriefError):
    """Konflik optimistic concurrency pada brief anak."""
    def __init__(self, message: str, current_revision: int, server_brief: Dict[str, Any]):
        super().__init__(message, status_code=409)
        self.current_revision = current_revision
        self.server_brief = server_brief


def validate_brief_payload(data: Any, is_patch: bool = False) -> Dict[str, Any]:
    """Validasi dan normalisasi payload brief anak."""
    if not isinstance(data, dict):
        raise KidsBriefError("Payload brief harus berupa objek JSON.")

    result: Dict[str, Any] = {}

    # Validasi Title
    if "title" in data or not is_patch:
        raw_title = data.get("title")
        if not isinstance(raw_title, str) or not raw_title.strip():
            raise KidsBriefError("Judul brief harus diisi (maksimal 120 karakter).")
        title = raw_title.strip()
        if len(title) > MAX_TITLE_LENGTH:
            raise KidsBriefError(f"Judul brief terlalu panjang (maksimal {MAX_TITLE_LENGTH} karakter).")
        result["title"] = title

    # Validasi Tujuan Belajar
    if "learning_goal" in data or not is_patch:
        raw_goal = data.get("learning_goal", "")
        if raw_goal is None:
            raw_goal = ""
        if not isinstance(raw_goal, str):
            raise KidsBriefError("Tujuan belajar harus berupa teks.")
        goal = raw_goal.strip()
        if len(goal) > MAX_GOAL_LENGTH:
            raise KidsBriefError(f"Tujuan belajar terlalu panjang (maksimal {MAX_GOAL_LENGTH} karakter).")
        result["learning_goal"] = goal

    # Validasi Outline
    if "outline" in data or not is_patch:
        raw_outline = data.get("outline", "")
        if raw_outline is None:
            raw_outline = ""
        if not isinstance(raw_outline, str):
            raise KidsBriefError("Outline harus berupa teks.")
        outline = raw_outline.strip()
        if len(outline) > MAX_OUTLINE_LENGTH:
            raise KidsBriefError(f"Outline terlalu panjang (maksimal {MAX_OUTLINE_LENGTH} karakter).")
        result["outline"] = outline

    # Validasi Catatan Aset
    if "asset_notes" in data or not is_patch:
        raw_assets = data.get("asset_notes", "")
        if raw_assets is None:
            raw_assets = ""
        if not isinstance(raw_assets, str):
            raise KidsBriefError("Catatan aset harus berupa teks.")
        assets = raw_assets.strip()
        if len(assets) > MAX_ASSETS_LENGTH:
            raise KidsBriefError(f"Catatan aset terlalu panjang (maksimal {MAX_ASSETS_LENGTH} karakter).")
        result["asset_notes"] = assets

    # Validasi Target Durasi
    if "target_duration" in data or not is_patch:
        raw_duration = data.get("target_duration", 30)
        if type(raw_duration) is not int or raw_duration not in ALLOWED_DURATIONS:
            raise KidsBriefError("Target durasi harus integer 15, 30, 45 atau 60.")
        duration = raw_duration
        result["target_duration"] = duration

    # Validasi Kategori
    if "category" in data or not is_patch:
        category = data.get("category", "warna")
        if not isinstance(category, str) or category not in CATEGORIES:
            raise KidsBriefError("Kategori brief tidak valid.")
        result["category"] = category

    # Validasi Idea ID referensi opsional
    if "idea_id" in data:
        raw_idea = data.get("idea_id")
        if raw_idea is None:
            result["idea_id"] = None
        elif isinstance(raw_idea, str) and raw_idea in {i["idea_id"] for i in IDEAS}:
            result["idea_id"] = raw_idea
        else:
            raise KidsBriefError("Referensi ide tidak valid.")
    elif not is_patch:
        result["idea_id"] = None

    for key, allowed in (("age_band", ALLOWED_AGE_BAND), ("language", ALLOWED_LANGUAGE)):
        if key in data and data[key] != allowed:
            raise KidsBriefError(f"{key} harus {allowed}.")
    for key in ("created_at", "updated_at", "revision", "brief_id"):
        if key in data:
            raise KidsBriefError(f"{key} dikelola server dan tidak boleh dikirim.")

    # Age band dan language terkunci pada MVP Studio Anak
    result["age_band"] = ALLOWED_AGE_BAND
    result["language"] = ALLOWED_LANGUAGE

    return result


def is_valid_brief_id(brief_id: str) -> bool:
    """Periksa apakah brief_id berupa 32 karakter hex yang aman."""
    return bool(isinstance(brief_id, str) and re.fullmatch(r"[a-f0-9]{32}", brief_id))


def get_brief_path(briefs_dir: Path, brief_id: str) -> Path:
    """Dapatkan path file brief yang divalidasi dari traversal."""
    if not is_valid_brief_id(brief_id):
        raise KidsBriefError("Format ID brief tidak valid.", status_code=400)
    path = briefs_dir / f"{brief_id}.json"
    if path.is_symlink():
        raise KidsBriefError("Akses tautan simbolik ditolak.", status_code=400)
    return path


def save_brief_atomic(briefs_dir: Path, brief: Dict[str, Any]) -> None:
    """Tulis brief ke disk secara atomik menggunakan file sementara."""
    briefs_dir.mkdir(parents=True, exist_ok=True)
    brief_id = brief.get("brief_id")
    target_path = get_brief_path(briefs_dir, brief_id)

    payload = json.dumps(brief, ensure_ascii=False, indent=2)
    # Tulis ke file sementara dalam folder yang sama agar operasi replace bersifat atomik
    fd, temp_path = tempfile.mkstemp(prefix="brief_", suffix=".tmp", dir=str(briefs_dir))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, target_path)
    except Exception:
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except OSError:
            pass
        raise


def read_brief(briefs_dir: Path, brief_id: str) -> Optional[Dict[str, Any]]:
    """Baca detail satu brief dari disk."""
    try:
        target_path = get_brief_path(briefs_dir, brief_id)
    except KidsBriefError:
        return None

    if not target_path.is_file():
        return None

    try:
        with open(target_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and data.get("brief_id") == brief_id:
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return None


def list_briefs(briefs_dir: Path, page: int = 1, page_size: int = 10, category: Optional[str] = None) -> Dict[str, Any]:
    """Daftar brief lokal dengan pagination dan filter kategori opsional."""
    if not briefs_dir.exists():
        return {"briefs": [], "total": 0, "filtered_total": 0, "page": 1, "page_size": page_size, "total_pages": 1}

    briefs: List[Dict[str, Any]] = []
    for item in briefs_dir.iterdir():
        if item.is_symlink() or not item.name.endswith(".json"):
            continue
        stem = item.stem
        if not is_valid_brief_id(stem):
            continue
        brief = read_brief(briefs_dir, stem)
        if brief:
            briefs.append(brief)

    # Urutkan berdasarkan updated_at desc, lalu created_at desc
    briefs.sort(key=lambda b: (b.get("updated_at", ""), b.get("created_at", ""), b.get("brief_id", "")), reverse=True)
    total = len(briefs)

    filtered = briefs
    if category and category in CATEGORIES:
        filtered = [b for b in briefs if b.get("category") == category]

    filtered_total = len(filtered)
    total_pages = max(1, (filtered_total + page_size - 1) // page_size)
    actual_page = max(1, min(page, total_pages))
    offset = (actual_page - 1) * page_size
    paged_briefs = filtered[offset:offset + page_size]

    return {
        "briefs": paged_briefs,
        "total": total,
        "filtered_total": filtered_total,
        "page": actual_page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


def delete_brief(briefs_dir: Path, brief_id: str) -> bool:
    """Hapus brief dari disk."""
    target_path = get_brief_path(briefs_dir, brief_id)
    if not target_path.exists():
        return False
    try:
        target_path.unlink()
        return True
    except OSError:
        return False


def format_brief_txt(brief: Dict[str, Any]) -> str:
    """Format brief anak menjadi dokumen teks rencana produksi yang rapi."""
    title = brief.get("title", "Brief Tanpa Judul")
    category = CATEGORIES.get(brief.get("category", ""), {}).get("label", brief.get("category", "-"))
    duration = brief.get("target_duration", 30)
    goal = brief.get("learning_goal") or "-"
    outline = brief.get("outline") or "-"
    asset_notes = brief.get("asset_notes") or "-"
    revision = brief.get("revision", 1)
    idea_ref = brief.get("idea_id") or "Kustom (orisinal)"
    updated_at = brief.get("updated_at") or datetime.now(timezone.utc).isoformat()

    lines = [
        "=" * 80,
        "BRIEF PRODUKSI KONTEN ANAK (3–5 TAHUN · BAHASA INDONESIA)",
        "Kelip Studio — Studio Anak",
        "=" * 80,
        f"Judul Kerja      : {title}",
        f"Target Usia      : 3–5 tahun",
        f"Bahasa           : Bahasa Indonesia",
        f"Target Durasi    : {duration} detik",
        f"Kategori         : {category}",
        f"Tujuan Belajar   : {goal}",
        f"Referensi Ide    : {idea_ref}",
        f"Revisi Brief     : {revision}",
        f"Terakhir Diubah  : {updated_at}",
        "",
        "-" * 80,
        "OUTLINE PRODUKSI (Pembukaan – Kegiatan – Penutup)",
        "-" * 80,
        outline,
        "",
        "-" * 80,
        "CATATAN ASET & SUMBER REKAMAN",
        "-" * 80,
        asset_notes,
        "",
        "-" * 80,
        "PANDUAN KUALITAS & KEBIJAKAN PLATFORM",
        "-" * 80,
        "• Satu konsep dan jawaban yang jelas per klip; beri konteks sebelum pertanyaan.",
        "• Narasi bahasa Indonesia sederhana dan sesuai dengan objek yang benar-benar ditampilkan.",
        "• Tempo visual tenang, tanpa efek cepat, suara mengejutkan, atau loop tanpa akhir.",
        "• Tidak meminta data diri anak atau ajakan komentar publik (sesuai prinsip Made for Kids).",
        "• Menggunakan aset rekaman orisinal atau berizin resmi.",
        "=" * 80,
    ]
    return "\n".join(lines)
