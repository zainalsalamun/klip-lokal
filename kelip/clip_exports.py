"""Derived clip exports. Inputs are server-owned paths and immutable settings snapshots."""
from pathlib import Path
import subprocess
import cv2
import numpy as np
from . import watermark
from .media_quality import ENCODER_PRESET, ENCODER_CRF, ENCODER_LOOKAHEAD


def render_export(ffmpeg, source, destination, config, assets_dir, *, kind, frame_time=0, ratio='vertical'):
    cap = cv2.VideoCapture(str(source))
    try:
        width, height = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps, frames = cap.get(cv2.CAP_PROP_FPS), cap.get(cv2.CAP_PROP_FRAME_COUNT)
        duration = frames / fps if fps > 0 else 0
    finally:
        cap.release()
    if width < 1 or height < 1 or duration <= 0:
        raise ValueError('Berkas klip tidak dapat dibaca.')
    if frame_time < 0 or frame_time >= duration:
        raise ValueError('Waktu frame harus berada di dalam durasi klip.')
    asset = None
    if config.get('enabled') and config.get('type') == 'logo':
        asset = next((assets_dir / (config['asset_id'] + ext) for ext in ('.png', '.jpg')
                      if (assets_dir / (config['asset_id'] + ext)).is_file()), None)
        if asset is None:
            raise ValueError('Logo tidak tersedia. Pilih aset lain lalu simpan draft.')
    if kind == 'thumbnail':
        # Extract through FFmpeg for accurate seeking; decoding via OpenCV is only raster IO.
        frame = destination.with_suffix('.frame.png')
        try:
            run(ffmpeg, ['-ss', str(frame_time), '-i', str(source), '-frames:v', '1', str(frame)])
            image = cv2.imread(str(frame))
            if image is None:
                raise ValueError('Frame tidak tersedia pada waktu tersebut.')
            out_w, out_h = (1080, 1920) if ratio == 'vertical' else (1280, 720)
            scale = min(out_w / width, out_h / height)
            resized = cv2.resize(image, (max(1, round(width * scale)), max(1, round(height * scale))))
            canvas = np.zeros((out_h, out_w, 3), dtype=np.uint8)
            h, w = resized.shape[:2]
            canvas[(out_h-h)//2:(out_h-h)//2+h, (out_w-w)//2:(out_w-w)//2+w] = resized
            composed = watermark.composite_watermark(canvas, config, asset)
            if not cv2.imwrite(str(destination), composed):
                raise OSError('Gagal menulis thumbnail.')
        finally:
            frame.unlink(missing_ok=True)
    else:
        if not config.get('enabled'):
            raise ValueError('Aktifkan dan simpan watermark sebelum mengekspor MP4 watermark.')
        # Generate a static RGBA overlay using the exact existing compositing routine.
        # White over black gives coverage; using two backgrounds preserves black text/logos.
        black = watermark.composite_watermark(np.zeros((height, width, 3), np.uint8), config, asset)
        white = watermark.composite_watermark(np.full((height, width, 3), 255, np.uint8), config, asset)
        alpha = np.clip(1 - (white.astype(float) - black.astype(float)).mean(axis=2) / 255, 0, 1)
        colors = np.divide(black, alpha[:, :, None], out=np.zeros_like(black, dtype=float), where=alpha[:, :, None] > 0)
        rgba = np.dstack([np.clip(colors, 0, 255).astype(np.uint8), (alpha * 255).round().astype(np.uint8)])
        overlay = destination.with_suffix('.overlay.png')
        try:
            if not cv2.imwrite(str(overlay), rgba):
                raise OSError('Gagal menulis overlay.')
            run(ffmpeg, ['-i', str(source), '-i', str(overlay), '-filter_complex', '[0:v][1:v]overlay=0:0:format=auto[v]',
                         '-map', '[v]', '-map', '0:a?', '-c:v', 'libx264', '-threads', '2', '-preset', ENCODER_PRESET,
                         '-crf', ENCODER_CRF, '-x264-params', ENCODER_LOOKAHEAD, '-pix_fmt', 'yuv420p', '-c:a', 'copy', '-movflags', '+faststart', str(destination)])
        finally:
            overlay.unlink(missing_ok=True)


def run(ffmpeg, args):
    result = subprocess.run([ffmpeg, '-hide_banner', '-y', '-threads', '2', '-filter_complex_threads', '1', *args], capture_output=True, text=True, timeout=3600)
    if result.returncode:
        raise RuntimeError('Ekspor gagal: ' + result.stderr[-1000:])
