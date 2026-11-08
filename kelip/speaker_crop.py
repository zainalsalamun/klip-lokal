"""Local face/mouth-motion estimate for vertical framing; no identity recognition."""
import math
import wave
from pathlib import Path


def speech_levels(audio, start, end, step=.25):
    import numpy as np
    with wave.open(str(audio), 'rb') as stream:
        rate = stream.getframerate()
        stream.setpos(min(stream.getnframes(), int(start * rate)))
        samples = np.frombuffer(stream.readframes(int((end-start)*rate)), dtype='<i2').astype('float32') / 32768
    size = max(1, int(rate*step))
    return [float(np.sqrt(np.mean(samples[i:i+size]**2))) for i in range(0, len(samples), size)]


class SpeakerTracker:
    """Require sustained mouth activity before switching; limit camera travel."""
    def __init__(self):
        self.center = .5
        self.speaker = None
        self.challenger = None
        self.votes = 0
        self.last_switch = -10

    def update(self, faces, talking, time):
        if faces:
            current = min(faces, key=lambda f: abs(f['center']-(self.speaker if self.speaker is not None else .5)))
            if self.speaker is None:
                current = max(faces, key=lambda f: f['area'])
                self.speaker = current['center']
            best = max(faces, key=lambda f: f['activity'])
            # Motion is only a proxy: do not switch on ambient silence or a single frame.
            challenger = talking and best['activity'] > max(.025, current['activity']*1.5) and abs(best['center']-current['center']) > .12
            if challenger:
                self.votes = self.votes+1 if self.challenger is not None and abs(best['center']-self.challenger) < .1 else 1
                self.challenger = best['center']
                if self.votes >= 4 and time-self.last_switch >= 1.5:
                    current = best
                    self.last_switch = time
                    self.votes = 0
            else:
                self.challenger = None
                self.votes = 0
            self.speaker = current['center']
        target = self.speaker if self.speaker is not None else .5
        self.center += max(-.035, min(.035, (target-self.center)*.35))
        return self.center


def smooth_crop_points(samples, frame_times, max_x, viewport_width, cuts=()):
    """Interpolate target positions, then apply time-based critically damped camera motion.

    Face samples stay ~4 Hz. Camera commands use actual decoded frame PTS, including VFR.
    Scene cuts reset the camera rather than panning across unrelated shots.
    """
    if not samples or not frame_times:
        return []
    import bisect
    targets = sorted(samples)
    times = [p[0] for p in targets]
    cut_times = sorted(cuts)
    cut_index = 0
    position = max(0., min(float(max_x), float(targets[0][1])))
    velocity = 0.
    previous_time = frame_times[0]
    result = []
    omega = 8.0
    max_speed = viewport_width * .65
    max_acceleration = viewport_width * 2.4
    dead_zone = viewport_width * .02
    for time in frame_times:
        right = bisect.bisect_right(times, time)
        left = max(0, right-1)
        target = float(targets[left][1])
        # Never interpolate across a shot boundary.
        if right < len(targets) and not any(times[left] < c <= times[right] for c in cut_times):
            span = times[right]-times[left]
            mix = max(0., min(1., (time-times[left])/span)) if span else 0.
            target += (targets[right][1]-target)*mix
        reset = False
        while cut_index < len(cut_times) and cut_times[cut_index] <= time:
            if cut_times[cut_index] > previous_time:
                reset = True
            cut_index += 1
        if reset:
            position, velocity = target, 0.
        else:
            remaining = max(0., time-previous_time)
            while remaining > 1e-9:
                dt = min(remaining, 1/120)
                error = target-position
                # Brake tiny tracking jitter rather than following every face-detector fluctuation.
                if abs(error) < dead_zone:
                    error = 0.
                acceleration = max(-max_acceleration, min(max_acceleration, omega*omega*error-2*omega*velocity))
                velocity = max(-max_speed, min(max_speed, velocity+acceleration*dt))
                position += velocity*dt
                if position < 0 or position > max_x:
                    position = max(0., min(float(max_x), position)); velocity = 0.
                remaining -= dt
        result.append((round(time, 6), round(max(0., min(float(max_x), position)))))
        previous_time = time
    return result


def crop_plan(source, audio, start, end, width, height):
    import av
    import cv2
    import numpy as np
    from .media_quality import scaled_size
    levels = speech_levels(audio, start, end)
    detector = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    if detector.empty():
        raise RuntimeError('Model deteksi wajah tidak tersedia')
    tracker = SpeakerTracker()
    previous = []
    samples, frame_times, cuts = [], [], []
    previous_scene = None
    detected = 0
    max_x = 0
    with av.open(str(source)) as video:
        stream = video.streams.video[0]
        stream.codec_context.thread_count = 2
        video.seek(max(0, int(start / stream.time_base)), stream=stream, backward=True)
        next_time = start
        for frame in video.decode(stream):
            if frame.time is None or frame.time < start:
                continue
            if frame.time >= end:
                break
            relative = frame.time-start
            if frame_times and relative <= frame_times[-1]:
                continue
            frame_times.append(relative)
            if frame.time < next_time:
                continue
            next_time = frame.time + .25
            small = frame.reformat(width=640, height=max(1, round(frame.height*640/frame.width)), format='gray').to_ndarray()
            scene = cv2.resize(small, (64,36)).astype('float32')/255
            scene_cut = previous_scene is not None and float(np.abs(scene-previous_scene).mean()) > .28
            previous_scene = scene
            if scene_cut:
                tracker = SpeakerTracker(); previous = []; cuts.append(relative)
            boxes = detector.detectMultiScale(small, scaleFactor=1.15, minNeighbors=5, minSize=(35,35))
            faces = []
            for x,y,w,h in boxes:
                center = (x+w/2)/small.shape[1]
                patch = cv2.resize(small[y:y+h,x:x+w], (48,48)).astype('float32') / 255
                nearest = min(previous, key=lambda f: abs(f['center']-center), default=None)
                activity = 0
                if nearest is not None and abs(nearest['center']-center) < .1:
                    delta = np.abs(patch-nearest['patch'])
                    activity = max(0, float(delta[28:45,10:38].mean()-delta[5:22,10:38].mean()))
                faces.append(dict(center=center, area=int(w*h), activity=activity, patch=patch))
            previous = faces
            if faces:
                detected += 1
            level = levels[min(len(levels)-1, int(relative/.25))] if levels else 0
            tracker.update(faces, level > .008, relative)
            center = tracker.speaker if tracker.speaker is not None else .5
            scaled_width, _ = scaled_size(frame.width, frame.height, width, height)
            max_x = scaled_width-width
            x = max(0, min(max_x, center*scaled_width-width/2))
            samples.append((relative, x))
    if not detected:
        return [], 0
    points = smooth_crop_points(samples, frame_times, max_x, width, cuts)
    if points:
        points[0] = (0., points[0][1])
    return points, detected
