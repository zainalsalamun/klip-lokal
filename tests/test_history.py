import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import app as module


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.data = patch.object(module, "DATA", Path(self.temp.name))
        self.memory = patch.object(module, "jobs", {})
        self.data.start(); self.memory.start()
        self.client = module.app.test_client()

    def tearDown(self):
        self.memory.stop(); self.data.stop(); self.temp.cleanup()

    def create(self, video_id):
        with patch.object(module.threading, "Thread"):
            response = self.client.post("/api/jobs", data={"url": "https://youtu.be/" + video_id})
        self.assertEqual(response.status_code, 202)
        return response.json["id"]

    def test_previous_results_survive_new_job_and_restart(self):
        first = self.create("first")
        clip = dict(file="clip-1.mp4", url=f"/files/{first}/clip-1.mp4", start=0, end=15, text="test")
        (module.DATA / first / "clip-1.mp4").write_bytes(b"saved video")
        module.update(first, title="First video", done=True, status="Selesai", progress=100, clips=[clip])
        second = self.create("second")
        summary = self.client.get("/api/jobs").json["jobs"]
        self.assertEqual([j["id"] for j in summary], [second, first])
        self.assertEqual(summary[1]["clip_count"], 1)
        self.assertEqual(summary[1]["source_url"], "https://youtu.be/first")
        self.assertNotIn("clips", summary[1])
        self.assertEqual(self.client.post("/api/jobs", data={"url": "https://youtu.be/third"}).status_code, 409)
        module.jobs.clear()  # Simulate a new server process reading saved records.
        old = self.client.get(f"/api/jobs/{first}").json
        self.assertEqual(len(old["clips"]), 1)
        for key, value in clip.items():
            self.assertEqual(old["clips"][0][key], value)
        with self.client.get(clip["url"]) as response:
            self.assertEqual(response.data, b"saved video")
        interrupted = self.client.get(f"/api/jobs/{second}").json
        self.assertTrue(interrupted["done"])
        self.assertEqual(interrupted["status"], "Gagal")
        self.assertIn("terhenti", interrupted["error"])
        self.assertEqual(len(self.client.get("/api/jobs").json["jobs"]), 2)

    def test_legacy_and_corrupt_records(self):
        jid = "a" * 32
        folder = module.DATA / jid; folder.mkdir()
        (folder / "job.json").write_text(json.dumps(dict(done=True, status="Selesai", clips=[])))
        for suffix, content in [("b", "{"), ("c", "[]")]:
            bad = module.DATA / (suffix * 32); bad.mkdir(); (bad / "job.json").write_text(content)
        (module.DATA / "models").mkdir()
        history = self.client.get("/api/jobs").json["jobs"]
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["id"], jid)
        self.assertTrue(history[0]["created_at"])
        self.assertEqual(self.client.get('/api/jobs/invalid').status_code, 404)

    def test_upload_name_and_initial_record_saved(self):
        import io
        with patch.object(module.threading, "Thread"):
            response = self.client.post("/api/jobs", data={"video": (io.BytesIO(b"fixture"), "My video.mov")})
        jid = response.json["id"]
        record = json.loads((module.DATA / jid / "job.json").read_text())
        self.assertEqual(record["title"], "My video.mov")
        self.assertEqual(record["source_name"], "My video.mov")
        self.assertTrue(record["created_at"])
        self.assertFalse(list(module.DATA.glob("*/*.tmp")))

    def test_delete_removes_all_artifacts_and_preserves_other_jobs_and_models(self):
        first = self.create("delete-me")
        module.update(first, done=True, status="Selesai")
        folder = module.DATA / first
        for name in ["source.mp4", "audio.wav", "transcript.json", "clip-1.ass", "clip-1.mp4"]:
            (folder / name).write_text("fixture")
        models = module.DATA / "models"; models.mkdir(); (models / "model.bin").write_bytes(b"model")
        second = self.create("keep-me")
        response = self.client.delete(f"/api/jobs/{first}")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json["deleted"])
        self.assertFalse(folder.exists())
        self.assertNotIn(first, module.jobs)
        self.assertTrue((module.DATA / second).exists())
        self.assertTrue((models / "model.bin").exists())
        self.assertEqual(self.client.get(f"/api/jobs/{first}").status_code, 404)
        self.assertEqual(self.client.get(f"/files/{first}/clip-1.mp4").status_code, 404)
        self.assertEqual([job["id"] for job in self.client.get("/api/jobs").json["jobs"]], [second])

    def test_active_jobs_cannot_be_deleted_but_interrupted_jobs_can(self):
        jid = self.create("active")
        self.assertEqual(self.client.delete(f"/api/jobs/{jid}").status_code, 409)
        self.assertTrue((module.DATA / jid).exists())
        module.jobs.clear()
        self.assertEqual(self.client.delete(f"/api/jobs/{jid}").status_code, 200)
        self.assertFalse((module.DATA / jid).exists())

    def test_delete_rejects_invalid_paths_and_handles_disk_errors(self):
        self.assertEqual(self.client.delete('/api/jobs/models').status_code, 404)
        jid = self.create("failed-delete")
        module.update(jid, done=True)
        with patch.object(module.shutil, "rmtree", side_effect=PermissionError()):
            self.assertEqual(self.client.delete(f"/api/jobs/{jid}").status_code, 500)
        self.assertTrue((module.DATA / jid).exists())
        self.assertIn(jid, module.jobs)
        target = module.DATA / "protected"; target.mkdir()
        link = module.DATA / ("e" * 32); link.symlink_to(target, target_is_directory=True)
        self.assertEqual(self.client.delete('/api/jobs/' + "e" * 32).status_code, 404)
        self.assertTrue(target.exists())


if __name__ == "__main__":
    unittest.main()
