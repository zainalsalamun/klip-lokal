"""
Watermark Video dan Thumbnail untuk Klip Lokal.

Mengelola:
- Validasi konfigurasi watermark (posisi 9 anchor, rasio lebar 5-30%, opasitas 10-100%, margin 0-10%).
- Validasi, sanitasi, dan penyimpanan logo aset (PNG alpha & JPG, max 5 MiB, max 4096x4096px, anti-bomb, anti-animasi).
- Penyimpanan preset lokal dengan ID stabil dan optimistic concurrency.
- Perhitungan geometri penempatan overlay dan deteksi benturan subtitle.
- Engine compositing raster berbasis OpenCV untuk frame video & gambar.
"""

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import tempfile
import cv2
import numpy as np

VALID_POSITIONS = {
    "top_left", "top_center", "top_right",
    "center_left", "center", "center_right",
    "bottom_left", "bottom_center", "bottom_right"
}

VALID_TEXT_COLORS = {"white", "black"}
VALID_TEXT_TREATMENTS = {"outline", "panel", "none"}

MAX_LOGO_BYTES = 5 * 1024 * 1024  # 5 MiB
MAX_DIMENSION = 4096
MAX_PIXELS = 4096 * 4096
MAX_TEXT_LENGTH = 60
MAX_PRESET_NAME_LENGTH = 80

MIN_WIDTH_RATIO = 0.05
MAX_WIDTH_RATIO = 0.30
MIN_OPACITY = 0.10
MAX_OPACITY = 1.00
MIN_MARGIN_RATIO = 0.00
MAX_MARGIN_RATIO = 0.10

DEFAULT_WATERMARK_CONFIG = {
    "enabled": False,
    "type": "text",
    "text": "",
    "asset_id": None,
    "asset_width": None,
    "asset_height": None,
    "position": "top_right",
    "width_ratio": 0.15,
    "opacity": 0.70,
    "margin_ratio": 0.03,
    "text_color": "white",
    "text_treatment": "outline"
}


class WatermarkError(Exception):
    """Base exception untuk validasi dan operasi watermark."""
    pass


class PayloadTooLargeError(WatermarkError):
    """Ukuran file melebihi batas maksimum."""
    pass


class WatermarkConflictError(WatermarkError):
    """Konflik konkurensi optimistik."""
    def __init__(self, message, current_revision=None):
        super().__init__(message)
        self.current_revision = current_revision


def sanitize_text(text: str) -> str:
    """Membersihkan teks watermark dari karakter berbahaya dan baris baru."""
    if not isinstance(text, str):
        return ""
    # Hapus newline dan carriage return, batasi satu baris
    single_line = re.sub(r"[\r\n\t]+", " ", text).strip()
    return single_line[:MAX_TEXT_LENGTH]


def get_asset_dimensions(assets_dir: Path, asset_id: str) -> tuple[int, int] | None:
    """Membaca dimensi (width, height) dari file aset logo di disk secara aman."""
    if not asset_id or not re.fullmatch(r"[a-f0-9]{16,64}", str(asset_id)):
        return None
    for ext in (".png", ".jpg"):
        asset_file = assets_dir / f"{asset_id}{ext}"
        if asset_file.exists():
            img = cv2.imread(str(asset_file), cv2.IMREAD_UNCHANGED)
            if img is not None:
                h, w = img.shape[:2]
                return (w, h)
    return None


def validate_watermark_config(raw_config: dict, assets_dir: Path | None = None) -> dict:
    """Memvalidasi dan menormalisasi konfigurasi watermark sesuai PRD."""
    if not isinstance(raw_config, dict):
        raise WatermarkError("Konfigurasi watermark harus berupa object JSON.")

    enabled = bool(raw_config.get("enabled", False))
    wm_type = str(raw_config.get("type", "text")).strip().lower()
    if wm_type not in ("text", "logo"):
        raise WatermarkError("Tipe watermark harus 'text' atau 'logo'.")

    position = str(raw_config.get("position", "top_right")).strip().lower()
    if position not in VALID_POSITIONS:
        raise WatermarkError(f"Posisi watermark '{position}' tidak valid. Pilihan: {', '.join(sorted(VALID_POSITIONS))}.")

    # Validasi angka (width_ratio, opacity, margin_ratio)
    def parse_float(val, name, min_v, max_v, default_v):
        if val is None:
            return default_v
        try:
            f = float(val)
        except (ValueError, TypeError):
            raise WatermarkError(f"Nilai {name} harus berupa angka.")
        if math.isnan(f) or math.isinf(f):
            raise WatermarkError(f"Nilai {name} tidak boleh NaN atau Infinity.")
        if f < min_v or f > max_v:
            raise WatermarkError(f"Nilai {name} ({f}) harus berada dalam rentang {min_v} - {max_v}.")
        return round(f, 4)

    width_ratio = parse_float(raw_config.get("width_ratio"), "width_ratio", MIN_WIDTH_RATIO, MAX_WIDTH_RATIO, 0.15)
    opacity = parse_float(raw_config.get("opacity"), "opacity", MIN_OPACITY, MAX_OPACITY, 0.70)
    margin_ratio = parse_float(raw_config.get("margin_ratio"), "margin_ratio", MIN_MARGIN_RATIO, MAX_MARGIN_RATIO, 0.03)

    text = sanitize_text(raw_config.get("text", ""))
    text_color = str(raw_config.get("text_color", "white")).strip().lower()
    if text_color not in VALID_TEXT_COLORS:
        text_color = "white"

    text_treatment = str(raw_config.get("text_treatment", "outline")).strip().lower()
    if text_treatment not in VALID_TEXT_TREATMENTS:
        text_treatment = "outline"

    asset_id = raw_config.get("asset_id")
    if asset_id is not None:
        asset_id = str(asset_id).strip()
        if not re.fullmatch(r"[a-f0-9]{16,64}", asset_id):
            raise WatermarkError("ID aset watermark tidak valid.")

    asset_w = None
    asset_h = None
    if enabled:
        if wm_type == "text":
            if not text:
                raise WatermarkError("Teks watermark tidak boleh kosong jika watermark aktif.")
        elif wm_type == "logo":
            if not asset_id:
                raise WatermarkError("Aset logo harus dipilih jika watermark logo aktif.")
            if assets_dir:
                dims = get_asset_dimensions(assets_dir, asset_id)
                if not dims:
                    raise WatermarkError(f"File aset logo '{asset_id}' tidak ditemukan di library server.")
                asset_w, asset_h = dims
            else:
                raw_w = raw_config.get("asset_width")
                raw_h = raw_config.get("asset_height")
                if isinstance(raw_w, int) and isinstance(raw_h, int) and raw_w > 0 and raw_h > 0:
                    asset_w, asset_h = raw_w, raw_h
    elif wm_type == "logo" and asset_id:
        if assets_dir:
            dims = get_asset_dimensions(assets_dir, asset_id)
            if dims:
                asset_w, asset_h = dims
        else:
            raw_w = raw_config.get("asset_width")
            raw_h = raw_config.get("asset_height")
            if isinstance(raw_w, int) and isinstance(raw_h, int) and raw_w > 0 and raw_h > 0:
                asset_w, asset_h = raw_w, raw_h

    return {
        "enabled": enabled,
        "type": wm_type,
        "text": text,
        "asset_id": asset_id if wm_type == "logo" else None,
        "asset_width": asset_w if wm_type == "logo" else None,
        "asset_height": asset_h if wm_type == "logo" else None,
        "position": position,
        "width_ratio": width_ratio,
        "opacity": opacity,
        "margin_ratio": margin_ratio,
        "text_color": text_color,
        "text_treatment": text_treatment
    }


def validate_and_save_logo(file_bytes: bytes, assets_dir: Path) -> dict:
    """
    Memvalidasi bytes logo yang diunggah dan menyimpannya secara atomik ke assets_dir.
    Memeriksa: ukuran file <= 5 MiB, decode valid PNG/JPG, dimensi <= 4096px, anti decompression bomb, anti animasi.
    """
    if len(file_bytes) > MAX_LOGO_BYTES:
        raise PayloadTooLargeError(f"Ukuran file logo ({len(file_bytes) / (1024*1024):.2f} MiB) melebihi batas 5 MiB.")

    if len(file_bytes) < 8:
        raise WatermarkError("File terlalu kecil atau bukan gambar yang valid.")

    # Deteksi magic bytes
    is_png = file_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    is_jpg = file_bytes.startswith(b"\xff\xd8")

    if not is_png and not is_jpg:
        raise WatermarkError("Format gambar tidak didukung. Harap unggah file PNG (dengan transparansi) atau JPG.")

    if is_png and b"acTL" in file_bytes:
        raise WatermarkError("Gambar animasi (Animated PNG) tidak diperbolehkan. Harap gunakan logo statis.")

    # Decode menggunakan OpenCV
    buf = np.frombuffer(file_bytes, dtype=np.uint8)
    img = cv2.imdecode(buf, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise WatermarkError("File gambar rusak atau gagal didecode.")

    h, w = img.shape[:2]
    if w < 10 or h < 10:
        raise WatermarkError(f"Dimensi gambar terlalu kecil ({w}x{h}). Minimal 10x10 piksel.")
    if w > MAX_DIMENSION or h > MAX_DIMENSION:
        raise WatermarkError(f"Dimensi gambar ({w}x{h}) melebihi batas maksimum 4096x4096 piksel.")
    if (w * h) > MAX_PIXELS:
        raise WatermarkError("Ukuran total piksel gambar melebihi batas aman (potensi decompression bomb).")
    uncompressed_bytes = w * h * (img.shape[2] if len(img.shape) > 2 else 1)
    if (uncompressed_bytes / max(1, len(file_bytes))) > 200.0 and uncompressed_bytes > 5 * 1024 * 1024:
        raise WatermarkError("Rasio dekompresi gambar terlalu tinggi (potensi decompression bomb).")

    # Batasi rasio ekstrem
    aspect = w / h
    if aspect > 20 or aspect < 0.05:
        raise WatermarkError("Rasio aspek gambar terlalu ekstrem untuk dijadikan watermark.")

    # Normalisasi raster: simpan bersih tanpa metadata berbahaya
    image_format = "png" if is_png else "jpg"
    if image_format == "png":
        success, normalized_bytes = cv2.imencode(".png", img)
    else:
        # Jika JPG memiliki 4 channel (sangat jarang), ubah ke 3 channel BGR
        if len(img.shape) == 3 and img.shape[2] == 4:
            img = img[:, :, :3]
        success, normalized_bytes = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 95])

    if not success:
        raise WatermarkError("Gagal menormalisasi file gambar.")

    norm_bytes = bytes(normalized_bytes)
    sha256 = hashlib.sha256(norm_bytes).hexdigest()
    asset_id = sha256[:16]
    target_file = assets_dir / f"{asset_id}.{image_format}"

    assets_dir.mkdir(parents=True, exist_ok=True)
    if not target_file.exists():
        tmp_file = assets_dir / f".tmp_{asset_id}_{datetime.now().timestamp()}"
        try:
            tmp_file.write_bytes(norm_bytes)
            tmp_file.replace(target_file)
        finally:
            if tmp_file.exists():
                try: tmp_file.unlink()
                except OSError: pass

    return {
        "asset_id": asset_id,
        "sha256": sha256,
        "width": w,
        "height": h,
        "image_format": image_format,
        "created_at": datetime.now(timezone.utc).isoformat()
    }


def calculate_watermark_box(config: dict, canvas_w: int, canvas_h: int, asset_w: int | None = None, asset_h: int | None = None) -> tuple[int, int, int, int, bool]:
    """
    Menghitung koordinat (x, y, w, h) kotak watermark pada kanvas (canvas_w, canvas_h).
    Mengembalikan (x, y, w, h, is_valid_fit).
    """
    shortest_dim = min(canvas_w, canvas_h)
    margin_ratio = config.get("margin_ratio")
    if margin_ratio is None:
        margin_ratio = 0.03
    margin = round(float(margin_ratio) * shortest_dim)

    width_ratio = config.get("width_ratio")
    if width_ratio is None:
        width_ratio = 0.15
    target_w = max(10, round(float(width_ratio) * canvas_w))

    wm_type = config.get("type", "text")
    if asset_w is None and config.get("asset_width"):
        asset_w = config.get("asset_width")
    if asset_h is None and config.get("asset_height"):
        asset_h = config.get("asset_height")
    if wm_type == "logo" and asset_w and asset_h and asset_w > 0:
        aspect = asset_h / asset_w
        target_h = max(10, round(target_w * aspect))
    else:
        # Teks: perkirakan tinggi dari lebar dan rasio font tipikal
        text_len = max(1, len(config.get("text", "Watermark")))
        # Tinggi baris teks sekitar 1/4 - 1/3 dari lebar jika teks pendek, atau proporsional
        char_w = target_w / max(4, text_len)
        target_h = max(12, round(char_w * 1.5))

    # Cek apakah ukuran melebihi kanvas setelah margin
    max_avail_w = canvas_w - (2 * margin)
    max_avail_h = canvas_h - (2 * margin)
    if target_w > max_avail_w or target_h > max_avail_h:
        return 0, 0, target_w, target_h, False

    pos = config.get("position", "top_right")

    # Posisi X
    if "left" in pos:
        x = margin
    elif "center" in pos and ("top" in pos or "bottom" in pos):
        x = (canvas_w - target_w) // 2
    elif pos == "center":
        x = (canvas_w - target_w) // 2
    else:  # right
        x = canvas_w - target_w - margin

    # Posisi Y
    if "top" in pos:
        y = margin
    elif "center" in pos and ("left" in pos or "right" in pos):
        y = (canvas_h - target_h) // 2
    elif pos == "center":
        y = (canvas_h - target_h) // 2
    else:  # bottom
        y = canvas_h - target_h - margin

    return x, y, target_w, target_h, True


def detect_subtitle_clash(
    config: dict,
    canvas_w: int = 720,
    canvas_h: int = 1280,
    asset_w: int | None = None,
    asset_h: int | None = None
) -> tuple[bool, str]:
    """
    Mendeteksi secara geometris apakah bounding box watermark bertabrakan dengan area subtitle (bawah).
    Area subtitle ASS vertikal (Alignment 2, MarginV 220 pada kanvas 1280) berada di sekitar y = 72%–92% kanvas.
    """
    if not config.get("enabled"):
        return False, ""
    if asset_w is None and config.get("asset_width"):
        asset_w = config.get("asset_width")
    if asset_h is None and config.get("asset_height"):
        asset_h = config.get("asset_height")
    x, y, w, h, valid = calculate_watermark_box(config, canvas_w, canvas_h, asset_w, asset_h)
    if not valid:
        return True, "Ukuran watermark melebihi ruang kanvas yang tersedia."

    sub_x1 = round(0.05 * canvas_w)
    sub_x2 = round(0.95 * canvas_w)
    sub_y1 = round(0.72 * canvas_h)
    sub_y2 = canvas_h

    overlap_w = max(0, min(x + w, sub_x2) - max(x, sub_x1))
    overlap_h = max(0, min(y + h, sub_y2) - max(y, sub_y1))

    if overlap_w > 0 and overlap_h > 0:
        return True, "Kotak watermark bertabrakan dengan area subtitle video (bawah)."
    return False, ""


def composite_watermark(canvas: np.ndarray, config: dict, asset_path: Path | None = None) -> np.ndarray:
    """
    Menerapkan watermark (teks atau logo) ke canvas numpy array (BGR).
    Mengembalikan array gambar baru hasil komposisi.
    """
    if not config.get("enabled"):
        return canvas

    out = canvas.copy()
    ch, cw = out.shape[:2]
    opacity = float(config.get("opacity", 0.70))
    wm_type = config.get("type", "text")

    if wm_type == "logo":
        if not asset_path or not asset_path.exists():
            raise WatermarkError(f"Aset logo watermark tidak ditemukan: {asset_path}")

        logo_img = cv2.imread(str(asset_path), cv2.IMREAD_UNCHANGED)
        if logo_img is None:
            raise WatermarkError("Gagal membaca file aset logo untuk compositing.")

        lh, lw = logo_img.shape[:2]
        x, y, w, h, fits = calculate_watermark_box(config, cw, ch, lw, lh)
        if not fits or w <= 0 or h <= 0:
            raise WatermarkError("Ukuran atau posisi watermark berada di luar batas kanvas gambar.")

        logo_resized = cv2.resize(logo_img, (w, h), interpolation=cv2.INTER_AREA)

        # Alpha compositing
        if len(logo_resized.shape) == 3 and logo_resized.shape[2] == 4:
            alpha = (logo_resized[:, :, 3].astype(np.float32) / 255.0) * opacity
            rgb = logo_resized[:, :, :3].astype(np.float32)
        else:
            alpha = np.full((h, w), opacity, dtype=np.float32)
            rgb = (logo_resized[:, :, :3] if len(logo_resized.shape) == 3 else np.repeat(logo_resized[:, :, np.newaxis], 3, axis=2)).astype(np.float32)

        alpha_3d = np.expand_dims(alpha, axis=-1)
        roi = out[y:y+h, x:x+w].astype(np.float32)
        blended = roi * (1.0 - alpha_3d) + rgb * alpha_3d
        out[y:y+h, x:x+w] = np.clip(blended, 0, 255).astype(np.uint8)

    elif wm_type == "text":
        text = config.get("text", "").strip()
        if not text:
            return out

        font = cv2.FONT_HERSHEY_DUPLEX
        shortest_dim = min(cw, ch)
        margin = round(config.get("margin_ratio", 0.03) * shortest_dim)
        target_w = max(10, round(config.get("width_ratio", 0.15) * cw))

        # Hitung font scale agar teks pas dengan target_w
        scale = 1.0
        (tw, th), base = cv2.getTextSize(text, font, scale, 1)
        if tw > 0:
            scale = scale * (target_w / tw)
        # Batasi batas scale minimum & maksimum yang masuk akal
        scale = max(0.2, min(scale, 3.0))
        (tw, th), base = cv2.getTextSize(text, font, scale, max(1, int(scale * 1.5)))

        padding_x = max(4, int(scale * 8))
        padding_y = max(4, int(scale * 6))
        total_w = tw + (padding_x * 2)
        total_h = th + base + (padding_y * 2)

        # Hitung posisi kotak
        pos = config.get("position", "top_right")
        if "left" in pos:
            x = margin
        elif "center" in pos and ("top" in pos or "bottom" in pos):
            x = (cw - total_w) // 2
        elif pos == "center":
            x = (cw - total_w) // 2
        else:
            x = cw - total_w - margin

        if "top" in pos:
            y = margin
        elif "center" in pos and ("left" in pos or "right" in pos):
            y = (ch - total_h) // 2
        elif pos == "center":
            y = (ch - total_h) // 2
        else:
            y = ch - total_h - margin

        x = max(0, min(x, cw - total_w))
        y = max(0, min(y, ch - total_h))

        # Siapkan overlay RGBA
        text_overlay = np.zeros((total_h, total_w, 4), dtype=np.uint8)
        color_choice = config.get("text_color", "white")
        treatment = config.get("text_treatment", "outline")

        fg_bgr = (255, 255, 255) if color_choice == "white" else (0, 0, 0)
        outline_bgr = (0, 0, 0) if color_choice == "white" else (255, 255, 255)

        tx = padding_x
        ty = padding_y + th

        if treatment == "panel":
            # Gambar panel semi-transparan di belakang
            panel_alpha = int(200 * opacity)
            panel_bgr = (20, 20, 20) if color_choice == "white" else (240, 240, 240)
            text_overlay[:, :] = (*panel_bgr, panel_alpha)

        if treatment == "outline":
            thickness_out = max(2, int(scale * 3.5))
            cv2.putText(text_overlay, text, (tx, ty), font, scale, (*outline_bgr, 255), thickness_out, cv2.LINE_AA)

        thickness_in = max(1, int(scale * 1.5))
        cv2.putText(text_overlay, text, (tx, ty), font, scale, (*fg_bgr, 255), thickness_in, cv2.LINE_AA)

        # Blend ke kanvas
        alpha = (text_overlay[:, :, 3].astype(np.float32) / 255.0) * opacity
        alpha_3d = np.expand_dims(alpha, axis=-1)
        rgb = text_overlay[:, :, :3].astype(np.float32)

        roi = out[y:y+total_h, x:x+total_w].astype(np.float32)
        blended = roi * (1.0 - alpha_3d) + rgb * alpha_3d
        out[y:y+total_h, x:x+total_w] = np.clip(blended, 0, 255).astype(np.uint8)

    return out


# Preset storage management
def load_presets(presets_file: Path) -> list[dict]:
    """Membaca daftar preset watermark dari file JSON."""
    if not presets_file.exists():
        return []
    try:
        data = json.loads(presets_file.read_text("utf-8"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "presets" in data:
            return data["presets"]
        return []
    except Exception:
        return []


def save_presets_atomic(presets_file: Path, presets: list[dict]):
    """Menyimpan daftar preset watermark secara atomik ke file JSON."""
    presets_file.parent.mkdir(parents=True, exist_ok=True)
    tmp_file = presets_file.with_suffix(".tmp")
    tmp_file.write_text(json.dumps(presets, ensure_ascii=False, indent=2), "utf-8")
    tmp_file.replace(presets_file)
