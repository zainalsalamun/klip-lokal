import copy
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import cv2
import numpy as np

from kelip import app
from kelip import watermark


class WatermarkTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)
        self.assets_dir = self.data_dir / "watermark-assets"
        self.presets_file = self.data_dir / "watermark-presets.json"
        self.assets_dir.mkdir(parents=True, exist_ok=True)

        self.app_patch = patch.multiple(
            app,
            DATA=self.data_dir,
            WATERMARK_ASSETS=self.assets_dir,
            WATERMARK_PRESETS=self.presets_file,
            jobs={}
        )
        self.app_patch.start()
        self.client = app.app.test_client()

    def tearDown(self):
        self.app_patch.stop()
        self.temp_dir.cleanup()

    def _create_sample_job(self, jid="1" * 32, num_clips=2):
        folder = self.data_dir / jid
        folder.mkdir(parents=True, exist_ok=True)
        job_data = {
            "id": jid,
            "title": "Video Uji Watermark",
            "done": True,
            "audience": "local",
            "created_at": "2026-11-05T10:00:00Z",
            "updated_at": "2026-11-05T10:00:00Z",
            "clips": [
                {
                    "start": 10.0,
                    "end": 25.0,
                    "text": f"Klip ke-{i+1}",
                    "caption": f"Caption ke-{i+1}",
                    "caption_source": "manual",
                    "metadata_revision": 1
                }
                for i in range(num_clips)
            ]
        }
        (folder / "job.json").write_text(json.dumps(job_data))
        return jid, job_data

    def _create_synthetic_png_bytes(self, w=120, h=80, with_alpha=True):
        img = np.zeros((h, w, 4 if with_alpha else 3), dtype=np.uint8)
        img[:, :, 2] = 255  # Red
        if with_alpha:
            img[:, :, 3] = 180  # ~70% alpha
        _, buf = cv2.imencode(".png", img)
        return bytes(buf)

    def _create_synthetic_jpg_bytes(self, w=120, h=80):
        img = np.full((h, w, 3), 200, dtype=np.uint8)  # Light grey
        img[10:30, 10:30] = (0, 0, 255)  # Red box
        _, buf = cv2.imencode(".jpg", img)
        return bytes(buf)

    # WM-01: Default nonaktif & history lama aman
    def test_wm01_default_disabled_and_legacy_history_safe(self):
        jid, _ = self._create_sample_job()
        res = self.client.get(f"/api/jobs/{jid}").json
        clip = res["clips"][0]

        self.assertIn("watermark", clip)
        self.assertFalse(clip["watermark"]["enabled"])
        self.assertEqual(clip["watermark"]["position"], "top_right")
        self.assertEqual(clip["watermark"]["width_ratio"], 0.15)
        self.assertEqual(clip["watermark"]["opacity"], 0.70)
        self.assertEqual(clip["watermark"]["margin_ratio"], 0.03)

        # GET tidak mengubah disk
        on_disk = json.loads((self.data_dir / jid / "job.json").read_text())
        self.assertNotIn("watermark", on_disk["clips"][0])

    # WM-02: Logo PNG alpha dan JPG pada kedua rasio (9:16 vertikal & 16:9 landscape)
    def test_wm02_logo_png_alpha_and_jpg_compositing(self):
        # 1. Upload PNG with alpha
        png_bytes = self._create_synthetic_png_bytes(100, 100, with_alpha=True)
        res_upload = self.client.post(
            "/api/watermark-assets",
            data={"file": (io.BytesIO(png_bytes), "logo.png")},
            content_type="multipart/form-data"
        )
        self.assertEqual(res_upload.status_code, 201)
        asset_id = res_upload.json["asset_id"]
        asset_file = self.assets_dir / f"{asset_id}.png"
        self.assertTrue(asset_file.exists())

        config_png = {
            "enabled": True,
            "type": "logo",
            "asset_id": asset_id,
            "position": "top_right",
            "width_ratio": 0.20,
            "opacity": 0.80,
            "margin_ratio": 0.05
        }

        # Vertical canvas 9:16 (720x1280)
        canvas_vert = np.zeros((1280, 720, 3), dtype=np.uint8)
        out_vert = watermark.composite_watermark(canvas_vert, config_png, asset_file)
        self.assertEqual(out_vert.shape, (1280, 720, 3))
        # Ensure red channel was drawn where logo is
        x, y, w, h, fits = watermark.calculate_watermark_box(config_png, 720, 1280, 100, 100)
        self.assertTrue(fits)
        self.assertGreater(out_vert[y + h // 2, x + w // 2, 2], 50)

        # Landscape canvas 16:9 (1280x720)
        canvas_land = np.zeros((720, 1280, 3), dtype=np.uint8)
        out_land = watermark.composite_watermark(canvas_land, config_png, asset_file)
        self.assertEqual(out_land.shape, (720, 1280, 3))

        # 2. Upload JPG (no alpha)
        jpg_bytes = self._create_synthetic_jpg_bytes(120, 60)
        res_jpg = self.client.post(
            "/api/watermark-assets",
            data={"file": (io.BytesIO(jpg_bytes), "logo.jpg")},
            content_type="multipart/form-data"
        )
        self.assertEqual(res_jpg.status_code, 201)
        jpg_id = res_jpg.json["asset_id"]
        jpg_file = self.assets_dir / f"{jpg_id}.jpg"
        self.assertTrue(jpg_file.exists())

        config_jpg = {
            "enabled": True,
            "type": "logo",
            "asset_id": jpg_id,
            "position": "bottom_left",
            "width_ratio": 0.15,
            "opacity": 0.50,
            "margin_ratio": 0.02
        }
        out_jpg = watermark.composite_watermark(canvas_vert, config_jpg, jpg_file)
        self.assertEqual(out_jpg.shape, (1280, 720, 3))

    # WM-03: Teks dengan karakter khusus, tanda kutip, metacharacter
    def test_wm03_text_sanitization_and_compositing(self):
        tricky_text = 'Klip "Spesial" & \'; rm -rf /; echo `whoami` \n baris baru'
        sanitized = watermark.sanitize_text(tricky_text)
        self.assertNotIn("\n", sanitized)
        self.assertLessEqual(len(sanitized), 60)

        config_text = {
            "enabled": True,
            "type": "text",
            "text": sanitized,
            "position": "top_center",
            "width_ratio": 0.25,
            "opacity": 0.90,
            "margin_ratio": 0.04,
            "text_color": "white",
            "text_treatment": "outline"
        }
        canvas = np.full((1280, 720, 3), 100, dtype=np.uint8)
        out = watermark.composite_watermark(canvas, config_text)
        self.assertEqual(out.shape, (1280, 720, 3))
        # Pixels must be modified by text
        self.assertFalse(np.array_equal(canvas, out))

    # WM-04: Sembilan posisi dan batas ukuran/margin
    def test_wm04_nine_positions_and_bounds_checking(self):
        canvas_w, canvas_h = 720, 1280
        for pos in watermark.VALID_POSITIONS:
            cfg = {
                "enabled": True,
                "type": "text",
                "text": "Position Test",
                "position": pos,
                "width_ratio": 0.15,
                "opacity": 0.70,
                "margin_ratio": 0.05
            }
            x, y, w, h, fits = watermark.calculate_watermark_box(cfg, canvas_w, canvas_h, 100, 100)
            self.assertTrue(fits, f"Position {pos} must fit")
            self.assertGreaterEqual(x, 0)
            self.assertGreaterEqual(y, 0)
            self.assertLessEqual(x + w, canvas_w)
            self.assertLessEqual(y + h, canvas_h)

        # Test clash detection on bottom positions
        self.assertTrue(watermark.detect_subtitle_clash({"enabled": True, "position": "bottom_right"})[0])
        self.assertTrue(watermark.detect_subtitle_clash({"enabled": True, "position": "bottom_center"})[0])
        self.assertFalse(watermark.detect_subtitle_clash({"enabled": True, "position": "top_right"})[0])

    # WM-05: Penolakan file rusak, animasi, kebesaran, decompression bomb
    def test_wm05_reject_invalid_corrupt_animated_and_oversized_images(self):
        # 1. Corrupt / fake file
        fake_bytes = b"<html><script>alert(1)</script></html>"
        res1 = self.client.post("/api/watermark-assets", data={"file": (io.BytesIO(fake_bytes), "fake.png")}, content_type="multipart/form-data")
        self.assertEqual(res1.status_code, 400)

        # 2. Animated PNG (contains acTL chunk)
        apng_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\x08acTL\x00\x00\x00\x02\x00\x00\x00\x00"
        res2 = self.client.post("/api/watermark-assets", data={"file": (io.BytesIO(apng_bytes), "anim.png")}, content_type="multipart/form-data")
        self.assertEqual(res2.status_code, 400)
        self.assertIn("animasi", res2.json["error"].lower())

        # 3. Oversized file (> 5 MiB)
        big_bytes = b"0" * (5 * 1024 * 1024 + 10)
        res3 = self.client.post("/api/watermark-assets", data={"file": (io.BytesIO(big_bytes), "big.png")}, content_type="multipart/form-data")
        self.assertEqual(res3.status_code, 413)

        # 4. Dimension bomb (> 4096px)
        with self.assertRaises(watermark.WatermarkError):
            watermark.validate_and_save_logo(self._create_synthetic_png_bytes(4097, 100), self.assets_dir)

    # WM-06: Simpan, refresh/restart, dan optimistic concurrency 409
    def test_wm06_draft_persistence_and_optimistic_concurrency(self):
        jid, _ = self._create_sample_job()
        clip_id = self.client.get(f"/api/jobs/{jid}").json["clips"][0]["clip_id"]

        new_config = {
            "enabled": True,
            "type": "text",
            "text": "Brand Ku",
            "position": "top_left",
            "width_ratio": 0.20,
            "opacity": 0.85,
            "margin_ratio": 0.04,
            "text_color": "white",
            "text_treatment": "outline"
        }

        # 1. Successful save
        res = self.client.patch(
            f"/api/jobs/{jid}/clips/{clip_id}/watermark",
            json={"watermark": new_config, "expected_revision": 1}
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json["watermark_revision"], 2)
        self.assertTrue(res.json["watermark"]["enabled"])

        # Disk has new config and watermark_revision 2
        on_disk = json.loads((self.data_dir / jid / "job.json").read_text())
        self.assertEqual(on_disk["clips"][0]["watermark_revision"], 2)
        self.assertEqual(on_disk["clips"][0]["watermark"]["text"], "Brand Ku")

        # 2. Second tab tries to save with stale expected_revision = 1 -> 409 Conflict
        res_conflict = self.client.patch(
            f"/api/jobs/{jid}/clips/{clip_id}/watermark",
            json={"watermark": new_config, "expected_revision": 1}
        )
        self.assertEqual(res_conflict.status_code, 409)
        self.assertTrue(res_conflict.json["conflict"])
        self.assertEqual(res_conflict.json["current_revision"], 2)

        # 3. Disk failure preserves in-memory state and returns 500
        with patch.object(app, "write_job_atomic", side_effect=OSError("Disk write failed")):
            res_fail = self.client.patch(
                f"/api/jobs/{jid}/clips/{clip_id}/watermark",
                json={"watermark": new_config, "expected_revision": 2}
            )
            self.assertEqual(res_fail.status_code, 500)

        # GET still returns watermark_revision 2
        res_get = self.client.get(f"/api/jobs/{jid}").json
        self.assertEqual(res_get["clips"][0]["watermark_revision"], 2)

    # WM-07: Snapshot konfigurasi & aset immutable (preset berubah tidak mengubah draft)
    def test_wm07_preset_crud_and_snapshot_isolation(self):
        # 1. Create preset
        p_cfg = {
            "enabled": True,
            "type": "text",
            "text": "Preset 1",
            "position": "top_right",
            "width_ratio": 0.15,
            "opacity": 0.70,
            "margin_ratio": 0.03
        }
        res_create = self.client.post(
            "/api/watermark-presets",
            json={"name": "Watermark Pojok Kanan", "configuration": p_cfg}
        )
        self.assertEqual(res_create.status_code, 201)
        preset_id = res_create.json["preset_id"]

        # 2. Apply to clip draft
        jid, _ = self._create_sample_job()
        clip_id = self.client.get(f"/api/jobs/{jid}").json["clips"][0]["clip_id"]

        self.client.patch(
            f"/api/jobs/{jid}/clips/{clip_id}/watermark",
            json={"watermark": p_cfg, "expected_revision": 1}
        )

        # 3. Modify preset in library
        p_cfg_updated = copy.deepcopy(p_cfg)
        p_cfg_updated["text"] = "Preset Telah Diubah"
        res_patch = self.client.patch(
            f"/api/watermark-presets/{preset_id}",
            json={"configuration": p_cfg_updated, "expected_revision": 1}
        )
        self.assertEqual(res_patch.status_code, 200)

        # 4. Verify clip draft retains original snapshot "Preset 1"
        clip_after = self.client.get(f"/api/jobs/{jid}").json["clips"][0]
        self.assertEqual(clip_after["watermark"]["text"], "Preset 1")

    # WM-08: Gagal jika aset logo hilang
    def test_wm08_missing_logo_asset_error(self):
        config_missing = {
            "enabled": True,
            "type": "logo",
            "asset_id": "0123456789abcdef",
            "position": "top_right"
        }
        jid, _ = self._create_sample_job()
        clip_id = self.client.get(f"/api/jobs/{jid}").json["clips"][0]["clip_id"]

        res = self.client.patch(
            f"/api/jobs/{jid}/clips/{clip_id}/watermark",
            json={"watermark": config_missing, "expected_revision": 1}
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("tidak ditemukan", res.json["error"].lower())

    # WM-09: Watermark diubah pada satu klip tidak mengubah klip lain / caption / subtitle
    def test_wm09_clip_isolation_and_caption_unaffected(self):
        jid, _ = self._create_sample_job(num_clips=2)
        job_res = self.client.get(f"/api/jobs/{jid}").json
        clip0_id = job_res["clips"][0]["clip_id"]
        clip1_id = job_res["clips"][1]["clip_id"]
        initial_caption = job_res["clips"][0]["caption"]

        # Update watermark on clip 0
        new_wm = {"enabled": True, "type": "text", "text": "Hanya Klip 0", "position": "top_left"}
        res = self.client.patch(
            f"/api/jobs/{jid}/clips/{clip0_id}/watermark",
            json={"watermark": new_wm, "expected_revision": 1}
        )
        self.assertEqual(res.status_code, 200)

        job_after = self.client.get(f"/api/jobs/{jid}").json
        c0 = job_after["clips"][0]
        c1 = job_after["clips"][1]

        # Clip 0 updated
        self.assertEqual(c0["watermark"]["text"], "Hanya Klip 0")
        self.assertEqual(c0["caption"], initial_caption)  # Caption unchanged
        self.assertEqual(c0["watermark_revision"], 2)
        self.assertEqual(c0["metadata_revision"], 1)  # Caption revision unchanged by watermark edit

        # Clip 1 completely unaffected
        self.assertFalse(c1["watermark"]["enabled"])
        self.assertEqual(c1["metadata_revision"], 1)

    # WM-10: Hapus satu job tidak menghapus logo/preset bersama
    def test_wm10_delete_job_preserves_shared_assets_and_presets(self):
        # 1. Upload logo
        png_bytes = self._create_synthetic_png_bytes(50, 50)
        res_up = self.client.post("/api/watermark-assets", data={"file": (io.BytesIO(png_bytes), "test.png")}, content_type="multipart/form-data")
        asset_id = res_up.json["asset_id"]

        # 2. Create preset
        self.client.post("/api/watermark-presets", json={"name": "Shared Preset", "configuration": {"enabled": True, "type": "text", "text": "Shared"}})

        # 3. Create and delete job
        jid, _ = self._create_sample_job()
        res_del = self.client.delete(f"/api/jobs/{jid}")
        self.assertEqual(res_del.status_code, 200)

        # Asset and preset still exist
        self.assertTrue((self.assets_dir / f"{asset_id}.png").exists())
        presets = self.client.get("/api/watermark-presets").json["presets"]
        self.assertEqual(len(presets), 1)
        self.assertEqual(presets[0]["name"], "Shared Preset")

    # WM-11: Resolusi 480p, 720p, 1080p normalisasi posisi & ukuran
    def test_wm11_resolution_scaling(self):
        cfg = {
            "enabled": True,
            "type": "text",
            "text": "Resolution Scaling Test",
            "position": "top_right",
            "width_ratio": 0.20,
            "opacity": 0.80,
            "margin_ratio": 0.05
        }
        for res_name, (w, h) in app.RESOLUTIONS.items():
            canvas = np.zeros((h, w, 3), dtype=np.uint8)
            out = watermark.composite_watermark(canvas, cfg)
            self.assertEqual(out.shape, (h, w, 3), f"Failed on resolution {res_name}")
            bx, by, bw, bh, fits = watermark.calculate_watermark_box(cfg, w, h, 200, 50)
            self.assertTrue(fits, f"Should fit on {res_name}")
            self.assertLessEqual(bx + bw, w)
            self.assertLessEqual(by + bh, h)

    # WM-12: Idempotent upload (upload ulang logo sama mengembalikan asset_id sama)
    def test_wm12_idempotent_logo_upload(self):
        png_bytes = self._create_synthetic_png_bytes(80, 80)
        res1 = self.client.post("/api/watermark-assets", data={"file": (io.BytesIO(png_bytes), "logo.png")}, content_type="multipart/form-data")
        res2 = self.client.post("/api/watermark-assets", data={"file": (io.BytesIO(png_bytes), "logo.png")}, content_type="multipart/form-data")

        self.assertEqual(res1.status_code, 201)
        self.assertEqual(res2.status_code, 201)
        self.assertEqual(res1.json["asset_id"], res2.json["asset_id"])
        self.assertEqual(res1.json["sha256"], res2.json["sha256"])

    # Regresi: Dua editor (caption dan watermark) dalam satu kartu tidak saling menimbulkan konflik
    def test_bidirectional_caption_and_watermark_in_single_card(self):
        jid, _ = self._create_sample_job()
        clip_id = self.client.get(f"/api/jobs/{jid}").json["clips"][0]["clip_id"]

        # 1. Simpan watermark: watermark_revision rev1 -> rev2; caption_revision tetap 1
        wm_cfg = {
            "enabled": True,
            "type": "text",
            "text": "Watermark Pertama",
            "position": "top_right",
            "width_ratio": 0.15,
            "opacity": 0.70,
            "margin_ratio": 0.03
        }
        res_wm1 = self.client.patch(
            f"/api/jobs/{jid}/clips/{clip_id}/watermark",
            json={"watermark": wm_cfg, "expected_revision": 1}
        )
        self.assertEqual(res_wm1.status_code, 200)
        self.assertEqual(res_wm1.json["watermark_revision"], 2)

        # 2. Editor caption di kartu yang sama mengirim expected_revision=1 -> HARUS SUKSES (bukan 409)
        res_cap1 = self.client.patch(
            f"/api/jobs/{jid}/clips/{clip_id}/caption",
            json={"caption": "Caption setelah watermark", "expected_revision": 1}
        )
        self.assertEqual(res_cap1.status_code, 200)
        self.assertEqual(res_cap1.json["caption_revision"], 2)

        # 3. Sekarang edit caption lagi: rev2 -> rev3; watermark_revision tetap 2
        res_cap2 = self.client.patch(
            f"/api/jobs/{jid}/clips/{clip_id}/caption",
            json={"caption": "Caption kedua setelah watermark", "expected_revision": 2}
        )
        self.assertEqual(res_cap2.status_code, 200)
        self.assertEqual(res_cap2.json["caption_revision"], 3)

        # 4. Sekarang edit watermark lagi dari kartu yang sama dengan expected_revision=2 -> HARUS SUKSES
        wm_cfg["text"] = "Watermark Kedua"
        res_wm2 = self.client.patch(
            f"/api/jobs/{jid}/clips/{clip_id}/watermark",
            json={"watermark": wm_cfg, "expected_revision": 2}
        )
        self.assertEqual(res_wm2.status_code, 200)
        self.assertEqual(res_wm2.json["watermark_revision"], 3)

        # Verifikasi data akhir di server
        final_clip = self.client.get(f"/api/jobs/{jid}").json["clips"][0]
        self.assertEqual(final_clip["caption"], "Caption kedua setelah watermark")
        self.assertEqual(final_clip["watermark"]["text"], "Watermark Kedua")
        self.assertEqual(final_clip["caption_revision"], 3)
        self.assertEqual(final_clip["watermark_revision"], 3)

    # Regresi: Konflik antar-tab tetap terlindungi untuk kedua domain
    def test_cross_tab_conflict_protection_both_domains(self):
        jid, _ = self._create_sample_job()
        clip_id = self.client.get(f"/api/jobs/{jid}").json["clips"][0]["clip_id"]

        # Tab A menyimpan watermark rev1 -> 2
        wm_cfg = {"enabled": True, "type": "text", "text": "Tab A Watermark", "position": "top_right"}
        res_a = self.client.patch(
            f"/api/jobs/{jid}/clips/{clip_id}/watermark",
            json={"watermark": wm_cfg, "expected_revision": 1}
        )
        self.assertEqual(res_a.status_code, 200)

        # Tab B mencoba menyimpan watermark dengan expected_revision=1 basi -> 409
        res_b_wm = self.client.patch(
            f"/api/jobs/{jid}/clips/{clip_id}/watermark",
            json={"watermark": wm_cfg, "expected_revision": 1}
        )
        self.assertEqual(res_b_wm.status_code, 409)
        self.assertTrue(res_b_wm.json["conflict"])
        self.assertEqual(res_b_wm.json["current_revision"], 2)

        # Tab A menyimpan caption rev1 -> 2
        res_a_cap = self.client.patch(
            f"/api/jobs/{jid}/clips/{clip_id}/caption",
            json={"caption": "Tab A Caption", "expected_revision": 1}
        )
        self.assertEqual(res_a_cap.status_code, 200)

        # Tab B mencoba menyimpan caption dengan expected_revision=1 basi -> 409
        res_b_cap = self.client.patch(
            f"/api/jobs/{jid}/clips/{clip_id}/caption",
            json={"caption": "Tab B Caption", "expected_revision": 1}
        )
        self.assertEqual(res_b_cap.status_code, 409)
        self.assertTrue(res_b_cap.json["conflict"])
        self.assertEqual(res_b_cap.json["current_revision"], 2)

    # Regresi: Deteksi benturan subtitle geometris (bukan sekadar cek string 'bottom')
    def test_detect_subtitle_clash_geometrical_overlap(self):
        # 1. Logo rasio tinggi 100x500 pada posisi center dengan width_ratio=0.3 di kanvas 720x1280
        # target_w = 216, target_h = 1080 -> y = (1280 - 1080) / 2 = 100
        # y + h = 1180, menembus area subtitle ASS (y=921..1177)
        tall_logo_cfg = {
            "enabled": True,
            "type": "logo",
            "position": "center",
            "width_ratio": 0.30,
            "margin_ratio": 0.03
        }
        clash, msg = watermark.detect_subtitle_clash(tall_logo_cfg, canvas_w=720, canvas_h=1280, asset_w=100, asset_h=500)
        self.assertTrue(clash, "Logo tinggi di center harus terdeteksi bentrok dengan subtitle")
        self.assertIn("bertabrakan", msg)

        # 2. Watermark teks kecil di top_right tidak bentrok
        top_cfg = {
            "enabled": True,
            "type": "text",
            "text": "Normal Brand",
            "position": "top_right",
            "width_ratio": 0.15,
            "margin_ratio": 0.03
        }
        clash_top, _ = watermark.detect_subtitle_clash(top_cfg, canvas_w=720, canvas_h=1280)
        self.assertFalse(clash_top, "Watermark di top_right tidak boleh terdeteksi bentrok")

        # 3. Watermark di bottom_center bentrok
        bot_cfg = {
            "enabled": True,
            "type": "text",
            "text": "Bottom Text",
            "position": "bottom_center",
            "width_ratio": 0.20,
            "margin_ratio": 0.02
        }
        clash_bot, _ = watermark.detect_subtitle_clash(bot_cfg, canvas_w=720, canvas_h=1280)
        self.assertTrue(clash_bot, "Watermark di bottom_center harus terdeteksi bentrok")

    # Regresi: 9 anchor positions pada 480p, 720p, 1080p dan margin 0
    def test_nine_anchors_all_resolutions_and_zero_margin(self):
        anchors = [
            "top_left", "top_center", "top_right",
            "center_left", "center", "center_right",
            "bottom_left", "bottom_center", "bottom_right"
        ]
        resolutions = [(480, 854), (720, 1280), (1080, 1920)]

        for w, h in resolutions:
            for margin_ratio in (0.0, 0.03, 0.10):
                for anchor in anchors:
                    cfg = {
                        "enabled": True,
                        "type": "text",
                        "text": "AnchorTest",
                        "position": anchor,
                        "width_ratio": 0.15,
                        "margin_ratio": margin_ratio
                    }
                    bx, by, bw, bh, fits = watermark.calculate_watermark_box(cfg, w, h)
                    self.assertTrue(fits, f"Failed fits for {anchor} at {w}x{h} margin={margin_ratio}")
                    self.assertGreaterEqual(bx, 0)
                    self.assertGreaterEqual(by, 0)
                    self.assertLessEqual(bx + bw, w)
                    self.assertLessEqual(by + bh, h)

                    # Verifikasi khusus margin 0: harus rapat di tepi (flush)
                    if margin_ratio == 0.0:
                        if "left" in anchor:
                            self.assertEqual(bx, 0, f"{anchor} margin 0 harus rapat kiri")
                        if "right" in anchor:
                            self.assertEqual(bx + bw, w, f"{anchor} margin 0 harus rapat kanan")
                        if "top" in anchor:
                            self.assertEqual(by, 0, f"{anchor} margin 0 harus rapat atas")
                        if "bottom" in anchor:
                            self.assertEqual(by + bh, h, f"{anchor} margin 0 harus rapat bawah")

    # Regresi: Anti decompression bomb dan batas dimensi minimum 10px
    def test_anti_decompression_bomb_and_min_dimension(self):
        # 1. Gambar lebih kecil dari 10x10 harus ditolak
        tiny_png = self._create_synthetic_png_bytes(8, 8)
        res_tiny = self.client.post("/api/watermark-assets", data={"file": (io.BytesIO(tiny_png), "tiny.png")}, content_type="multipart/form-data")
        self.assertEqual(res_tiny.status_code, 400)
        self.assertIn("terlalu kecil", res_tiny.json["error"])

        # 2. Gambar 10x10 harus diterima
        min_png = self._create_synthetic_png_bytes(10, 10)
        res_min = self.client.post("/api/watermark-assets", data={"file": (io.BytesIO(min_png), "min.png")}, content_type="multipart/form-data")
        self.assertEqual(res_min.status_code, 201)

    # Regresi review kedua: Endpoint PATCH membaca dimensi logo nyata tanpa NameError, mendeteksi benturan logo tinggi, dan mempertahankan dimensi di reload/preset/konflik
    def test_endpoint_tall_logo_clash_detection_and_dimension_persistence(self):
        # 1. Upload logo tinggi 100x500 (rasio 5:1)
        tall_png = self._create_synthetic_png_bytes(w=100, h=500, with_alpha=True)
        res_upload = self.client.post(
            "/api/watermark-assets",
            data={"file": (io.BytesIO(tall_png), "tall.png")},
            content_type="multipart/form-data"
        )
        self.assertEqual(res_upload.status_code, 201)
        asset_id = res_upload.json["asset_id"]
        self.assertEqual(res_upload.json["width"], 100)
        self.assertEqual(res_upload.json["height"], 500)

        # 2. PATCH watermark pada klip: logo di center dengan lebar 30% pada kanvas default 720x1280
        # Di kanvas 720x1280, target_w = 216, target_h = 1080 -> y = 100 -> bottom edge = 1180
        # Subtitle zone ASS mulai y=922 -> HARUS terdeteksi clash_detected: True
        jid, _ = self._create_sample_job()
        clip_id = self.client.get(f"/api/jobs/{jid}").json["clips"][0]["clip_id"]

        patch_cfg = {
            "enabled": True,
            "type": "logo",
            "asset_id": asset_id,
            "position": "center",
            "width_ratio": 0.30,
            "margin_ratio": 0.03,
            # Coba kirim dimensi palsu dari client; server HARUS menimpanya dengan dimensi file nyata di disk
            "asset_width": 9999,
            "asset_height": 1
        }

        res_patch = self.client.patch(
            f"/api/jobs/{jid}/clips/{clip_id}/watermark",
            json={"watermark": patch_cfg, "expected_revision": 1}
        )
        self.assertEqual(res_patch.status_code, 200)
        # Verifikasi deteksi benturan endpoint
        self.assertTrue(res_patch.json["clash_detected"], "Endpoint PATCH harus mendeteksi benturan logo tinggi di posisi center")
        self.assertIn("bertabrakan", res_patch.json["clash_message"])
        # Verifikasi dimensi divalidasi dari disk nyata, bukan dimensi palsu client
        self.assertEqual(res_patch.json["watermark"]["asset_width"], 100)
        self.assertEqual(res_patch.json["watermark"]["asset_height"], 500)

        # 3. Verifikasi GET /api/jobs/<jid> (reload/refresh) mempertahankan dimensi logo
        res_get = self.client.get(f"/api/jobs/{jid}").json
        saved_wm = res_get["clips"][0]["watermark"]
        self.assertEqual(saved_wm["asset_width"], 100)
        self.assertEqual(saved_wm["asset_height"], 500)

        # 4. Verifikasi simpan dan muat preset mempertahankan dimensi logo
        res_preset = self.client.post(
            "/api/watermark-presets",
            json={"name": "Preset Logo Tinggi", "configuration": saved_wm}
        )
        self.assertEqual(res_preset.status_code, 201)
        self.assertEqual(res_preset.json["configuration"]["asset_width"], 100)
        self.assertEqual(res_preset.json["configuration"]["asset_height"], 500)

        # 5. Verifikasi respon konflik 409 menyertakan server_watermark dengan dimensi lengkap
        res_conflict = self.client.patch(
            f"/api/jobs/{jid}/clips/{clip_id}/watermark",
            json={"watermark": patch_cfg, "expected_revision": 1}
        )
        self.assertEqual(res_conflict.status_code, 409)
        self.assertTrue(res_conflict.json["conflict"])
        self.assertEqual(res_conflict.json["server_watermark"]["asset_width"], 100)
        self.assertEqual(res_conflict.json["server_watermark"]["asset_height"], 500)


if __name__ == "__main__":
    unittest.main()
