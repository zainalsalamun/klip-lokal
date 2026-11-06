"""Input quality, output geometry and shared local encoding settings."""
import math
from pathlib import Path

SOURCE_HEIGHTS = {'1080':1080, '1440':1440, '2160':2160}
ENCODER_PRESET = 'fast'
ENCODER_CRF = '18'
SCALE_FLAGS = 'lanczos'


def download_options(folder, ffmpeg, node, source_quality='1080'):
    height = SOURCE_HEIGHTS[source_quality]
    return {
        'js_runtimes':{'node':{'path':str(node)}},
        'format':f'bestvideo[height<={height}]+bestaudio/best[height<={height}]',
        'merge_output_format':'mp4', 'ffmpeg_location':str(ffmpeg),
        'outtmpl':str(Path(folder)/'source.%(ext)s'), 'noplaylist':True, 'quiet':True,
        'socket_timeout':30, 'retries':2, 'max_filesize':2*1024**3,
    }


def downloaded_path(ydl, info, folder):
    # prepare_filename may refer to the pre-merge extension. Prefer postprocessor metadata.
    candidates = [info.get('filepath'), *(d.get('filepath') for d in info.get('requested_downloads', []) or [])]
    candidates += [str(Path(folder)/'source.mp4'), ydl.prepare_filename(info)]
    root = Path(folder).resolve()
    for name in candidates:
        if not name:
            continue
        path = Path(name)
        if path.suffix.lower() not in ('.mp4','.mkv','.webm','.mov') or not path.is_file():
            continue
        if path.is_symlink() or path.resolve().parent != root:
            continue
        # A requested_download may still point to a video-only component; skip components.
        if path.stem != 'source':
            continue
        return path
    raise RuntimeError('File sumber setelah penggabungan video/audio tidak ditemukan.')


def probe_media(path):
    import av
    try:
        with av.open(str(path)) as container:
            stream = container.streams.video[0]
            if stream.width <= 0 or stream.height <= 0:
                return None
            return {'width':stream.width, 'height':stream.height,
                    'fps':round(float(stream.average_rate), 4) if stream.average_rate else None,
                    'codec':stream.codec_context.name, 'bitrate':stream.bit_rate}
    except (OSError, ValueError, IndexError, av.FFmpegError):
        return None


def output_quality(source_media, width, height, *, foreground_height=None):
    if not source_media:
        return {'source_known':False, 'warning':'Resolusi sumber belum dapat dibaca.'}
    sw, sh = source_media['width'], source_media['height']
    main_height = foreground_height or height
    scale = max(width/sw, main_height/sh)
    warning = ''
    if scale > 1.05:
        warning = f'Sumber {sw} × {sh} diperbesar {scale:.2f}× untuk area gambar {width} × {main_height}. Detail mengikuti sumber, bukan label resolusi output.'
    return {'source_known':True, 'source_width':sw, 'source_height':sh,
            'output_width':width, 'output_height':height, 'upscale_factor':round(scale, 3),
            'effective_crop_width':round(width/scale), 'effective_crop_height':round(main_height/scale),
            'warning':warning}


def scaled_size(sw, sh, width, height):
    scale = max(width/sw, height/sh)
    return math.ceil(sw*scale/2)*2, math.ceil(sh*scale/2)*2
