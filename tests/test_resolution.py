import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import av
import app as module


class ResolutionTests(unittest.TestCase):
    def test_all_resolutions_encode_video_audio_and_subtitles(self):
        with tempfile.TemporaryDirectory(prefix="klip resolution ") as directory:
            root = Path(directory)
            source = root / "source.mp4"
            module.run(["-f", "lavfi", "-i", "color=c=blue:size=320x180:rate=10",
                        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=16000",
                        "-t", "0.6", "-c:v", "libx264", "-c:a", "aac", source])
            subtitles = root / "captions.ass"
            module.write_subs(subtitles, [dict(start=0, end=.6, text="Subtitle test")], 0, .6)
            for resolution, size in module.RESOLUTIONS.items():
                with self.subTest(resolution=resolution):
                    output = root / f"{resolution}.mp4"
                    module.render_clip(source, subtitles, output, 0, .6, resolution)
                    with av.open(str(output)) as video:
                        self.assertEqual((video.streams.video[0].width, video.streams.video[0].height), size)
                        self.assertTrue(video.streams.audio)
                        frame = next(video.decode(video=0)).to_ndarray(format="rgb24")
                        # White subtitle glyphs must be burned into the otherwise blue video.
                        self.assertTrue(((frame[:, :, 0] > 180) & (frame[:, :, 1] > 180) & (frame[:, :, 2] > 180)).any())

    def test_dynamic_crop_changes_actual_exported_pixels(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); source=root/'source.mp4'
            module.run(['-f','lavfi','-i','color=c=red:size=640x360:rate=10',
                        '-vf','drawbox=x=320:y=0:w=320:h=360:color=blue:t=fill',
                        '-t','2','-c:v','libx264',source])
            (root/'audio.wav').write_bytes(b'fixture: plan mocked')
            subtitles=root/'captions.ass'
            module.write_subs(subtitles,[],0,2)
            out=root/'out.mp4'
            with patch('speaker_crop.crop_plan',return_value=([(0,0),(1,1040)],8)):
                framing=module.render_clip(source,subtitles,out,0,2,'480')
            self.assertEqual(framing['mode'],'speaker_estimate')
            with av.open(str(out)) as video:
                frames=list(video.decode(video=0))
                first=frames[0].to_ndarray(format='rgb24').mean(axis=(0,1))
                last=frames[-1].to_ndarray(format='rgb24').mean(axis=(0,1))
                self.assertGreater(first[0],first[2]+100)
                self.assertGreater(last[2],last[0]+100)

    def test_setting_persists_and_invalid_setting_rejected(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(module, "DATA", Path(directory)), patch.object(module, "jobs", {}), patch.object(module.threading, "Thread") as thread:
            client = module.app.test_client()
            self.assertEqual(client.post("/api/jobs", data={"url":"https://youtu.be/test", "resolution":"4k"}).status_code, 400)
            for resolution in module.RESOLUTIONS:
                response = client.post("/api/jobs", data={"video":(io.BytesIO(b"fixture"), "test.mp4"), "resolution":resolution})
                self.assertEqual(response.status_code, 202)
                jid = response.json["id"]
                self.assertEqual(thread.call_args.kwargs["args"][6], resolution)
                module.update(jid, done=True)
                module.jobs.clear()
                self.assertEqual(client.get(f"/api/jobs/{jid}").json["resolution"], resolution)
                self.assertEqual(client.get("/api/jobs").json["jobs"][0]["resolution"], resolution)


if __name__ == "__main__":
    unittest.main()
