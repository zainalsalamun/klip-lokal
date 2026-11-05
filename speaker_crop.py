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


def crop_plan(source, audio, start, end, width, height):
    import av
    import cv2
    import numpy as np
    levels = speech_levels(audio, start, end)
    detector = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    if detector.empty():
        raise RuntimeError('Model deteksi wajah tidak tersedia')
    tracker = SpeakerTracker()
    previous = []
    points = []
    detected = 0
    with av.open(str(source)) as video:
        stream = video.streams.video[0]
        video.seek(max(0, int(start / stream.time_base)), stream=stream, backward=True)
        next_time = start
        for frame in video.decode(stream):
            if frame.time is None or frame.time < next_time: continue
            if frame.time >= end: break
            relative = frame.time-start
            next_time = frame.time + .25
            small = frame.reformat(width=640, height=max(1, round(frame.height*640/frame.width)), format='gray').to_ndarray()
            boxes = detector.detectMultiScale(small, scaleFactor=1.15, minNeighbors=5, minSize=(35,35))
            faces = []
            for x,y,w,h in boxes:
                center = (x+w/2)/small.shape[1]
                patch = cv2.resize(small[y:y+h,x:x+w], (48,48)).astype('float32') / 255
                nearest = min(previous, key=lambda f: abs(f['center']-center), default=None)
                activity = 0
                if nearest is not None and abs(nearest['center']-center) < .1:
                    delta = np.abs(patch-nearest['patch'])
                    # Subtract upper-face motion to reduce head/camera-motion triggers.
                    activity = max(0, float(delta[28:45,10:38].mean()-delta[5:22,10:38].mean()))
                faces.append(dict(center=center, area=int(w*h), activity=activity, patch=patch))
            previous = faces
            if faces: detected += 1
            level = levels[min(len(levels)-1, int(relative/.25))] if levels else 0
            center = tracker.update(faces, level > .008, relative)
            factor = max(width/frame.width, height/frame.height)
            scaled_width = math.ceil(frame.width*factor)
            x = max(0, min(scaled_width-width, round(center*scaled_width-width/2)))
            points.append((round(relative,3), x))
    return points if detected else [], detected
