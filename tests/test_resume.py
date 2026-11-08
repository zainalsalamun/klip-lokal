import copy
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import wave

from kelip import app as m


class ResumeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.patches = [
            patch.object(m, "DATA", self.root), patch.object(m, "jobs", {}),
            patch.object(m, "active_export", None), patch.object(m, "caption_requests", 0),
        ]
        for item in self.patches:
            item.start()
        self.jid = "e" * 32
        self.folder = self.root / self.jid
        self.folder.mkdir()
        self.job = dict(id=self.jid, done=True, error="Interrupted", status="Gagal",
                        source_url="https://youtu.be/fixture", duration=30, count=3,
                        language="id", audience="local", clips=[])
        m.write_job_atomic(self.jid, self.job)
        self.client = m.app.test_client()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.tmp.cleanup()

    def test_resume_is_reserved_atomically_and_rejects_double_click(self):
        with patch.object(m.threading, "Thread") as thread:
            response = self.client.post(f"/api/jobs/{self.jid}/resume")
            self.assertEqual(response.status_code, 202)
            self.assertTrue(thread.call_args.kwargs["kwargs"]["resume"])
            self.assertEqual(self.client.post(f"/api/jobs/{self.jid}/resume").status_code, 409)
            self.assertFalse(json.loads((self.folder / "job.json").read_text())["done"])

    def test_disk_failure_does_not_publish_reservation(self):
        with patch.object(m, "write_job_atomic", side_effect=OSError("disk full")):
            self.assertEqual(self.client.post(f"/api/jobs/{self.jid}/resume").status_code, 500)
        self.assertNotIn(self.jid, m.jobs)
        self.assertTrue(json.loads((self.folder / "job.json").read_text())["done"])

    def test_thread_failure_can_be_retried_and_local_missing_source_explained(self):
        with patch.object(m.threading, "Thread") as thread:
            thread.return_value.start.side_effect = RuntimeError("start")
            self.assertEqual(self.client.post(f"/api/jobs/{self.jid}/resume").status_code, 500)
        self.assertTrue(m.jobs[self.jid]["done"])
        with patch.object(m.threading, "Thread"):
            self.assertEqual(self.client.post(f"/api/jobs/{self.jid}/resume").status_code, 202)
        m.jobs.clear()
        self.job["source_url"] = None
        m.write_job_atomic(self.jid, self.job)
        response = self.client.post(f"/api/jobs/{self.jid}/resume")
        self.assertEqual(response.status_code, 409)
        self.assertIn("Unggah kembali", response.json["error"])

    def test_resume_uses_source_transcript_and_finished_clip_after_restart(self):
        source = self.folder / "source.mp4"
        m.run(["-f", "lavfi", "-i", "color=c=blue:s=160x284:r=5:d=2",
               "-c:v", "libx264", source])
        segments = [dict(start=0, end=1, text="Kalimat pertama."),
                    dict(start=1, end=2, text="Kalimat kedua.")]
        (self.folder / "transcript.json").write_text(json.dumps(segments))
        m.jobs[self.jid] = dict(self.job, done=False, error=None, highlight_mode="ai")
        ranked = [{**segments[1], "highlight_reason": "insight"}, {**segments[0], "highlight_reason": "hook"}]
        def fail_second(source, ass, out, *args, **kwargs):
            if out.name == "clip-2.mp4":
                raise RuntimeError("render interrupted")
            shutil.copyfile(source, out)
            return {"mode": "fixture"}

        with patch.object(m, "candidates", return_value=segments), patch.object(m, "rank_candidates", return_value=ranked), \
                patch.object(m, "transcribe_audio") as transcribe, patch.object(m, "render_clip", side_effect=fail_second):
            m.process(self.jid, self.job["source_url"], None, 30, 3, "id", resume=True)
        transcribe.assert_not_called()
        failed = json.loads((self.folder / "job.json").read_text())
        self.assertTrue(failed["done"])
        self.assertEqual(len(failed["resume_clips"]), 1)
        self.assertEqual(failed["highlight_selection"], ranked)
        original_clip = (self.folder / "clip-1.mp4").read_bytes()
        m.jobs.clear()
        m.jobs[self.jid] = dict(m.read_job(self.jid), done=False, error=None)
        with patch.object(m, "rank_candidates") as rank, patch.object(m, "render_clip", return_value={"mode": "fixture"}) as render, \
                patch.object(m, "summarize", side_effect=m.CaptionUnavailable("offline")):
            m.process(self.jid, self.job["source_url"], None, 30, 3, "id", resume=True)
        self.assertEqual(render.call_count, 1)
        rank.assert_not_called()
        self.assertEqual(render.call_args.args[2].name, "clip-2.mp4")
        self.assertEqual((self.folder / "clip-1.mp4").read_bytes(), original_clip)
        self.assertFalse(m.jobs[self.jid].get("error"))
        self.assertEqual(len(m.jobs[self.jid]["clips"]), 2)
        self.assertEqual(m.jobs[self.jid]["clips"][0]["highlight_reason"], "insight")

    def test_highlight_mode_is_validated_and_stored(self):
        with patch.object(m.threading, "Thread"):
            data = {"url": "https://youtu.be/fixture", "highlight_mode": "unknown"}
            self.assertEqual(self.client.post("/api/jobs", data=data).status_code, 400)
            data["highlight_mode"] = "ai"
            self.assertEqual(self.client.post("/api/jobs", data={**data, "content_profile": "kids"}).status_code, 400)
            response = self.client.post("/api/jobs", data=data)
            self.assertEqual(response.status_code, 202)
            self.assertEqual(m.jobs[response.json["id"]]["highlight_mode"], "ai")

    def test_busy_exports_and_successful_jobs_cannot_resume(self):
        with patch.object(m, "active_export", ("other", "clip", "export")):
            self.assertEqual(self.client.post(f"/api/jobs/{self.jid}/resume").status_code, 409)
        self.job.pop("error")
        m.write_job_atomic(self.jid, self.job)
        self.assertEqual(self.client.post(f"/api/jobs/{self.jid}/resume").status_code, 409)

    def test_owned_whisper_model_released_on_error(self):
        with patch.object(m, "model", None), patch("faster_whisper.WhisperModel") as model:
            model.return_value.transcribe.side_effect = RuntimeError("transcription interrupted")
            with self.assertRaises(RuntimeError):
                m.transcribe_audio(self.folder / "audio.wav", "id", "local")
            self.assertIsNone(m.model)
            self.assertEqual(model.call_args.kwargs["cpu_threads"], 2)

    def test_long_audio_is_chunked_with_timestamps(self):
        audio = self.folder / "audio.wav"
        with wave.open(str(audio), "wb") as output:
            output.setparams((1, 2, 10, 0, "NONE", "not compressed"))
            output.writeframes(b"\0\0" * 3010)
        durations = []
        class Model:
            def transcribe(self, path, **kwargs):
                with wave.open(path, "rb") as chunk:
                    durations.append(chunk.getnframes() / chunk.getframerate())
                return iter([SimpleNamespace(start=0, end=.5, text="Test")]), None
        with patch.object(m, "model", Model()):
            segments = m.transcribe_audio(audio, "id", "local")
        self.assertEqual(durations, [300, 1])
        self.assertEqual(segments[1]["start"], 300)
        self.assertFalse((self.folder / "transcribe-chunk.wav").exists())


if __name__ == "__main__":
    unittest.main()
