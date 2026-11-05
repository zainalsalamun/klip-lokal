import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import app


class CaptionPersistenceTests(unittest.TestCase):
    def test_legacy_job_gets_deterministic_clip_id_and_persists_on_write(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(app, "DATA", Path(directory)), patch.object(app, "jobs", {}):
            jid = "1" * 32
            folder = app.DATA / jid
            folder.mkdir()
            original_data = {
                "done": True,
                "audience": "local",
                "clips": [
                    {"start": 10.5, "end": 25.5, "text": "Klip pertama"},
                    {"start": 30.0, "end": 45.0, "text": "Klip kedua"}
                ]
            }
            (folder / "job.json").write_text(json.dumps(original_data))

            client = app.app.test_client()
            res1 = client.get(f"/api/jobs/{jid}").json
            res2 = client.get(f"/api/jobs/{jid}").json

            # IDs must be present and deterministic across GETs
            clip_id_0 = res1["clips"][0]["clip_id"]
            clip_id_1 = res1["clips"][1]["clip_id"]
            self.assertTrue(clip_id_0)
            self.assertTrue(clip_id_1)
            self.assertNotEqual(clip_id_0, clip_id_1)
            self.assertEqual(clip_id_0, res2["clips"][0]["clip_id"])
            self.assertEqual(clip_id_1, res2["clips"][1]["clip_id"])

            # Verify GET did NOT write to disk
            on_disk_before = json.loads((folder / "job.json").read_text())
            self.assertNotIn("clip_id", on_disk_before["clips"][0])

            # Now write to first clip via PATCH
            patch_res = client.patch(
                f"/api/jobs/{jid}/clips/{clip_id_0}/caption",
                json={"caption": "Caption manual pertama", "expected_revision": 1}
            )
            self.assertEqual(patch_res.status_code, 200)
            self.assertEqual(patch_res.json["caption"], "Caption manual pertama")
            self.assertEqual(patch_res.json["caption_source"], "manual")
            self.assertEqual(patch_res.json["metadata_revision"], 2)

            # Verify disk was updated with schema_version = 2 and clip_id
            on_disk_after = json.loads((folder / "job.json").read_text())
            self.assertEqual(on_disk_after.get("schema_version"), 2)
            self.assertEqual(on_disk_after["clips"][0]["clip_id"], clip_id_0)
            self.assertEqual(on_disk_after["clips"][0]["caption"], "Caption manual pertama")
            self.assertEqual(on_disk_after["clips"][0]["caption_source"], "manual")
            self.assertEqual(on_disk_after["clips"][0]["metadata_revision"], 2)
            # Other clip preserves its deterministic ID when persisted
            self.assertEqual(on_disk_after["clips"][1]["clip_id"], clip_id_1)

    def test_save_manual_caption_persists_and_survives_reload(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(app, "DATA", Path(directory)), patch.object(app, "jobs", {}):
            jid = "2" * 32
            folder = app.DATA / jid
            folder.mkdir()
            (folder / "job.json").write_text(json.dumps({
                "schema_version": 2,
                "done": True,
                "audience": "local",
                "clips": [{
                    "clip_id": "clip0001",
                    "metadata_revision": 1,
                    "start": 0.0,
                    "end": 15.0,
                    "text": "Teks asli",
                    "caption": "Caption otomatis",
                    "caption_source": "extractive"
                }]
            }))
            client = app.app.test_client()

            # Save manual caption
            save_res = client.patch(
                f"/api/jobs/{jid}/clips/clip0001/caption",
                json={"caption": "Caption manual tersimpan", "expected_revision": 1}
            )
            self.assertEqual(save_res.status_code, 200)
            self.assertEqual(save_res.json["metadata_revision"], 2)
            self.assertEqual(save_res.json["caption_source"], "manual")

            # Simulate new server / clearing in-memory jobs cache
            app.jobs.clear()
            app.history_cache.clear()

            # GET should return the persisted manual caption
            get_res = client.get(f"/api/jobs/{jid}").json
            clip = get_res["clips"][0]
            self.assertEqual(clip["caption"], "Caption manual tersimpan")
            self.assertEqual(clip["caption_source"], "manual")
            self.assertEqual(clip["metadata_revision"], 2)
            self.assertEqual(clip["caption_language"], "unverified")
            self.assertTrue(clip["caption_updated_at"])

    def test_empty_caption_is_allowed_as_explicit_choice(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(app, "DATA", Path(directory)), patch.object(app, "jobs", {}):
            jid = "3" * 32
            folder = app.DATA / jid
            folder.mkdir()
            (folder / "job.json").write_text(json.dumps({
                "schema_version": 2,
                "done": True,
                "audience": "local",
                "clips": [{
                    "clip_id": "c1",
                    "metadata_revision": 1,
                    "caption": "Awalnya ada caption"
                }]
            }))
            client = app.app.test_client()
            res = client.patch(
                f"/api/jobs/{jid}/clips/c1/caption",
                json={"caption": "", "expected_revision": 1}
            )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json["caption"], "")
            self.assertEqual(res.json["caption_source"], "manual")

            # Missing caption field is rejected
            res_missing = client.patch(
                f"/api/jobs/{jid}/clips/c1/caption",
                json={"expected_revision": 2}
            )
            self.assertEqual(res_missing.status_code, 400)
            self.assertIn("caption wajib diisi", res_missing.json["error"])

    def test_validation_errors(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(app, "DATA", Path(directory)), patch.object(app, "jobs", {}):
            jid = "4" * 32
            folder = app.DATA / jid
            folder.mkdir()
            (folder / "job.json").write_text(json.dumps({
                "done": True,
                "clips": [{"clip_id": "c1", "metadata_revision": 1, "caption": "test"}]
            }))
            client = app.app.test_client()

            # Non-JSON payload
            res = client.patch(f"/api/jobs/{jid}/clips/c1/caption", data="not json", content_type="text/plain")
            self.assertEqual(res.status_code, 400)

            # Caption too long (>2000 chars)
            res = client.patch(f"/api/jobs/{jid}/clips/c1/caption", json={"caption": "x" * 2001, "expected_revision": 1})
            self.assertEqual(res.status_code, 400)
            self.assertIn("2.000 karakter", res.json["error"])

            # Caption not a string
            res = client.patch(f"/api/jobs/{jid}/clips/c1/caption", json={"caption": 12345, "expected_revision": 1})
            self.assertEqual(res.status_code, 400)

            # Missing expected_revision
            res = client.patch(f"/api/jobs/{jid}/clips/c1/caption", json={"caption": "halo"})
            self.assertEqual(res.status_code, 400)

            # Invalid expected_revision (bool, string, negative)
            for bad_rev in [True, False, "1", -1, 0]:
                res = client.patch(f"/api/jobs/{jid}/clips/c1/caption", json={"caption": "halo", "expected_revision": bad_rev})
                self.assertEqual(res.status_code, 400)

            # Nonexistent clip_id
            res = client.patch(f"/api/jobs/{jid}/clips/nonexistent/caption", json={"caption": "halo", "expected_revision": 1})
            self.assertEqual(res.status_code, 404)

            # Nonexistent job_id
            res = client.patch(f"/api/jobs/{'5'*32}/clips/c1/caption", json={"caption": "halo", "expected_revision": 1})
            self.assertEqual(res.status_code, 404)

    def test_optimistic_concurrency_conflict_409(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(app, "DATA", Path(directory)), patch.object(app, "jobs", {}):
            jid = "6" * 32
            folder = app.DATA / jid
            folder.mkdir()
            (folder / "job.json").write_text(json.dumps({
                "done": True,
                "clips": [{"clip_id": "c1", "metadata_revision": 1, "caption": "Versi awal"}]
            }))
            client = app.app.test_client()

            # Client 1 updates successfully
            res1 = client.patch(f"/api/jobs/{jid}/clips/c1/caption", json={"caption": "Edit tab 1", "expected_revision": 1})
            self.assertEqual(res1.status_code, 200)
            self.assertEqual(res1.json["metadata_revision"], 2)

            # Client 2 tries to update with outdated expected_revision = 1
            res2 = client.patch(f"/api/jobs/{jid}/clips/c1/caption", json={"caption": "Edit tab 2", "expected_revision": 1})
            self.assertEqual(res2.status_code, 409)
            self.assertTrue(res2.json.get("conflict"))
            self.assertEqual(res2.json["current_revision"], 2)
            self.assertEqual(res2.json["server_caption"], "Edit tab 1")

            # Client 2's failed edit must not overwrite server data
            current = client.get(f"/api/jobs/{jid}").json["clips"][0]
            self.assertEqual(current["caption"], "Edit tab 1")

    def test_ai_generation_cannot_overwrite_newer_manual_edit(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(app, "DATA", Path(directory)), patch.object(app, "jobs", {}):
            jid = "7" * 32
            folder = app.DATA / jid
            folder.mkdir()
            (folder / "job.json").write_text(json.dumps({
                "done": True,
                "audience": "local",
                "clips": [{"clip_id": "c1", "metadata_revision": 1, "text": "Menabung penting", "caption": "Versi awal"}]
            }))
            client = app.app.test_client()

            ai_summary_result = {
                "caption": "Ringkasan AI hasil lama",
                "caption_source": "ai_local",
                "caption_status": "ready"
            }

            # Simulate: AI summarize was called when revision was 1,
            # but while summarize was running, a manual edit was saved (bumping revision to 2)
            def summarize_with_concurrent_manual_edit(text, audience):
                client.patch(f"/api/jobs/{jid}/clips/c1/caption", json={"caption": "Edit manual yang lebih baru", "expected_revision": 1})
                return ai_summary_result

            with patch.object(app, "summarize", side_effect=summarize_with_concurrent_manual_edit):
                ai_res = client.post(f"/api/jobs/{jid}/clips/0/caption")

            # AI attempt must be rejected with 409 Conflict
            self.assertEqual(ai_res.status_code, 409)
            self.assertIn("manual", ai_res.json["error"])

            # Manual edit remains preserved on server
            clip = client.get(f"/api/jobs/{jid}").json["clips"][0]
            self.assertEqual(clip["caption"], "Edit manual yang lebih baru")
            self.assertEqual(clip["caption_source"], "manual")
            self.assertEqual(clip["metadata_revision"], 2)

    def test_disk_failure_does_not_mutate_resident_job_and_retry_succeeds(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(app, "DATA", Path(directory)), patch.object(app, "jobs", {}):
            jid = "8" * 32
            folder = app.DATA / jid
            folder.mkdir()
            initial_data = {
                "id": jid,
                "done": True,
                "clips": [{"clip_id": "c1", "metadata_revision": 1, "caption": "Versi awal tersimpan", "caption_source": "manual"}]
            }
            (folder / "job.json").write_text(json.dumps(initial_data))
            app.jobs[jid] = json.loads(json.dumps(initial_data))

            client = app.app.test_client()

            # Fail write_job_atomic
            with patch.object(app, "write_job_atomic", side_effect=OSError("Disk write error")):
                res = client.patch(f"/api/jobs/{jid}/clips/c1/caption", json={"caption": "Versi baru gagal", "expected_revision": 1})
                self.assertEqual(res.status_code, 500)
                self.assertIn("Gagal menyimpan ke disk", res.json["error"])

            # Verify in-memory resident jobs[jid] is completely unmutated
            self.assertEqual(app.jobs[jid]["clips"][0]["caption"], "Versi awal tersimpan")
            self.assertEqual(app.jobs[jid]["clips"][0]["metadata_revision"], 1)

            # Verify GET still returns old caption and old revision
            get_res = client.get(f"/api/jobs/{jid}").json
            self.assertEqual(get_res["clips"][0]["caption"], "Versi awal tersimpan")
            self.assertEqual(get_res["clips"][0]["metadata_revision"], 1)

            # Verify disk file still has old data
            disk_data = json.loads((folder / "job.json").read_text())
            self.assertEqual(disk_data["clips"][0]["caption"], "Versi awal tersimpan")
            self.assertEqual(disk_data["clips"][0]["metadata_revision"], 1)

            # Now retry with expected_revision=1 after disk recovers
            retry_res = client.patch(f"/api/jobs/{jid}/clips/c1/caption", json={"caption": "Versi baru sukses", "expected_revision": 1})
            self.assertEqual(retry_res.status_code, 200)
            self.assertEqual(retry_res.json["caption"], "Versi baru sukses")
            self.assertEqual(retry_res.json["metadata_revision"], 2)

            # Verify in-memory and disk both have the updated revision 2
            self.assertEqual(app.jobs[jid]["clips"][0]["caption"], "Versi baru sukses")
            self.assertEqual(app.jobs[jid]["clips"][0]["metadata_revision"], 2)
            disk_after = json.loads((folder / "job.json").read_text())
            self.assertEqual(disk_after["clips"][0]["caption"], "Versi baru sukses")
            self.assertEqual(disk_after["clips"][0]["metadata_revision"], 2)

    def test_disk_failure_does_not_corrupt_disk_only_job_and_retry_succeeds(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(app, "DATA", Path(directory)), patch.object(app, "jobs", {}):
            jid = "9" * 32
            folder = app.DATA / jid
            folder.mkdir()
            (folder / "job.json").write_text(json.dumps({
                "done": True,
                "clips": [{"clip_id": "c1", "metadata_revision": 1, "caption": "Versi disk lama"}]
            }))
            app.jobs.clear()

            client = app.app.test_client()

            with patch.object(app, "write_job_atomic", side_effect=OSError("Disk write error")):
                res = client.patch(f"/api/jobs/{jid}/clips/c1/caption", json={"caption": "Gagal", "expected_revision": 1})
                self.assertEqual(res.status_code, 500)

            # Verify disk and GET remain untouched
            get_res = client.get(f"/api/jobs/{jid}").json
            self.assertEqual(get_res["clips"][0]["caption"], "Versi disk lama")
            self.assertEqual(get_res["clips"][0]["metadata_revision"], 1)

            # Retry succeeds
            retry_res = client.patch(f"/api/jobs/{jid}/clips/c1/caption", json={"caption": "Sukses", "expected_revision": 1})
            self.assertEqual(retry_res.status_code, 200)
            self.assertEqual(retry_res.json["caption"], "Sukses")
            self.assertEqual(retry_res.json["metadata_revision"], 2)

    def test_stable_manual_caption_can_be_regenerated_by_ai_when_confirmed(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(app, "DATA", Path(directory)), patch.object(app, "jobs", {}):
            jid = "a" * 32
            folder = app.DATA / jid
            folder.mkdir()
            (folder / "job.json").write_text(json.dumps({
                "done": True,
                "audience": "local",
                "clips": [{
                    "clip_id": "c1",
                    "metadata_revision": 2,
                    "text": "Menabung penting untuk masa depan.",
                    "caption": "Manual edit pengguna",
                    "caption_source": "manual"
                }]
            }))
            client = app.app.test_client()

            ai_result = {
                "caption": "Ringkasan AI baru dari pembahasan.",
                "caption_source": "ai_local",
                "caption_status": "ready"
            }

            # 1. Regenerate with expected_revision=2 matches and succeeds!
            with patch.object(app, "summarize", return_value=ai_result) as mock_summarize:
                res = client.post(f"/api/jobs/{jid}/clips/c1/caption", json={"expected_revision": 2})
                self.assertEqual(res.status_code, 200)
                self.assertEqual(res.json["caption"], ai_result["caption"])
                self.assertEqual(res.json["caption_source"], "ai_local")
                self.assertEqual(res.json["metadata_revision"], 3)
                mock_summarize.assert_called_once()

            # Verify persisted to disk
            clip_disk = json.loads((folder / "job.json").read_text())["clips"][0]
            self.assertEqual(clip_disk["caption"], ai_result["caption"])
            self.assertEqual(clip_disk["caption_source"], "ai_local")
            self.assertEqual(clip_disk["metadata_revision"], 3)

            # 2. Legacy call without expected_revision on revision 3 also succeeds
            with patch.object(app, "summarize", return_value={"caption": "AI kedua", "caption_source": "ai_local", "caption_status": "ready"}):
                res2 = client.post(f"/api/jobs/{jid}/clips/0/caption")
                self.assertEqual(res2.status_code, 200)
                self.assertEqual(res2.json["caption"], "AI kedua")
                self.assertEqual(res2.json["metadata_revision"], 4)

    def test_ai_precheck_expected_revision_mismatch_returns_409_before_summarize(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(app, "DATA", Path(directory)), patch.object(app, "jobs", {}):
            jid = "b" * 32
            folder = app.DATA / jid
            folder.mkdir()
            (folder / "job.json").write_text(json.dumps({
                "done": True,
                "audience": "local",
                "clips": [{"clip_id": "c1", "metadata_revision": 3, "text": "Teks", "caption": "Teks"}]
            }))
            client = app.app.test_client()

            with patch.object(app, "summarize") as mock_summarize:
                res = client.post(f"/api/jobs/{jid}/clips/c1/caption", json={"expected_revision": 1})
                self.assertEqual(res.status_code, 409)
                self.assertTrue(res.json.get("conflict"))
                self.assertEqual(res.json["current_revision"], 3)
                # Ensure Ollama was not even called
                mock_summarize.assert_not_called()


if __name__ == "__main__":
    unittest.main()
