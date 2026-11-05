import copy
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from app import app
import kids_content


class KidsContentUnitTest(unittest.TestCase):
    """Unit test fungsi dan data modul kids_content."""

    def test_catalog_structure_and_editorial_provenance(self):
        """Memastikan minimal 10 ide terkurasi dengan atribut lengkap dan provenance editorial."""
        self.assertGreaterEqual(len(kids_content.IDEAS), 10)
        self.assertGreaterEqual(len(kids_content.CATEGORIES), 10)

        known_ids = set()
        for idea in kids_content.IDEAS:
            self.assertIn("idea_id", idea)
            self.assertNotIn(idea["idea_id"], known_ids)
            known_ids.add(idea["idea_id"])

            self.assertIn(idea["category"], kids_content.CATEGORIES)
            self.assertEqual(idea.get("age_band"), "3_5")
            self.assertEqual(idea.get("language"), "id")
            self.assertTrue(bool(idea.get("title")))
            self.assertTrue(bool(idea.get("learning_goal")))
            self.assertTrue(bool(idea.get("outline")))
            self.assertIn(idea.get("suggested_duration"), kids_content.ALLOWED_DURATIONS)
            self.assertTrue(bool(idea.get("asset_notes")))
            self.assertIn(idea.get("workflow_fit"), ("cocok dicoba dengan clipper ucapan", "rencana produksi; perlu pemilihan manual"))
            self.assertEqual(idea.get("provenance"), "editorial")

        # Pastikan sumber acuan platform terdefinisi
        self.assertGreaterEqual(len(kids_content.SOURCES), 2)
        for src in kids_content.SOURCES:
            self.assertTrue(src.get("label"))
            self.assertTrue(src.get("url", "").startswith("https://"))

    def test_validate_brief_payload_success_and_defaults(self):
        """Validasi payload yang valid dengan pembersihan whitespace dan default."""
        raw = {
            "title": "  Menghitung Tiga Bintang  ",
            "learning_goal": "  Belajar angka 1–3  ",
            "category": "hitung",
            "target_duration": 15,
            "outline": "Tunjukkan bintang satu per satu.",
            "asset_notes": "Bintang karton warna kuning.",
            "idea_id": "hitung-01",
        }
        res = kids_content.validate_brief_payload(raw)
        self.assertEqual(res["title"], "Menghitung Tiga Bintang")
        self.assertEqual(res["learning_goal"], "Belajar angka 1–3")
        self.assertEqual(res["category"], "hitung")
        self.assertEqual(res["target_duration"], 15)
        self.assertEqual(res["age_band"], "3_5")
        self.assertEqual(res["language"], "id")
        self.assertEqual(res["idea_id"], "hitung-01")

    def test_validate_brief_payload_rejections(self):
        """Validasi penolakan payload yang tidak valid sesuai batasan PRD."""
        # Payload bukan dict
        with self.assertRaises(kids_content.KidsBriefError) as ctx:
            kids_content.validate_brief_payload("string")
        self.assertEqual(ctx.exception.status_code, 400)

        # Title kosong / spasi saja
        with self.assertRaises(kids_content.KidsBriefError):
            kids_content.validate_brief_payload({"title": "   "})

        # Title terlalu panjang (> 120 kar)
        with self.assertRaises(kids_content.KidsBriefError):
            kids_content.validate_brief_payload({"title": "A" * 121})

        # Goal terlalu panjang (> 300 kar)
        with self.assertRaises(kids_content.KidsBriefError):
            kids_content.validate_brief_payload({"title": "Judul", "learning_goal": "A" * 301})

        # Outline terlalu panjang (> 2000 kar)
        with self.assertRaises(kids_content.KidsBriefError):
            kids_content.validate_brief_payload({"title": "Judul", "outline": "A" * 2001})

        # Assets terlalu panjang (> 2000 kar)
        with self.assertRaises(kids_content.KidsBriefError):
            kids_content.validate_brief_payload({"title": "Judul", "asset_notes": "A" * 2001})

        # Target duration tidak diizinkan
        with self.assertRaises(kids_content.KidsBriefError):
            kids_content.validate_brief_payload({"title": "Judul", "target_duration": 99})

    def test_format_brief_txt(self):
        """Format ekspor teks menghasilkan informasi terstruktur dan panduan kualitas."""
        brief = {
            "brief_id": "a" * 32,
            "revision": 2,
            "idea_id": "warna-01",
            "category": "warna",
            "target_duration": 30,
            "title": "Mana Benda Merah?",
            "learning_goal": "Mengenali warna merah",
            "outline": "Tunjukkan 3 benda lalu tunjuk yang merah.",
            "asset_notes": "Apel, daun, balok.",
            "updated_at": "2026-11-05T12:00:00Z",
        }
        txt = kids_content.format_brief_txt(brief)
        self.assertIn("BRIEF PRODUKSI KONTEN ANAK", txt)
        self.assertIn("Mana Benda Merah?", txt)
        self.assertIn("Revisi Brief     : 2", txt)
        self.assertIn("Target Durasi    : 30 detik", txt)
        self.assertIn("Made for Kids", txt)


class KidsBriefStorageTest(unittest.TestCase):
    """Pengujian persistensi disk, atomisitas, pagination dan isolasi brief."""

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="test_briefs_"))

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_atomic_crud_operations(self):
        """Menyimpan, membaca, mendaftar, dan menghapus brief dari disk."""
        brief_id = "0123456789abcdef0123456789abcdef"
        brief = {
            "brief_id": brief_id,
            "revision": 1,
            "title": "Bentuk Kotak & Segitiga",
            "learning_goal": "Mengenali bentuk",
            "category": "bentuk",
            "target_duration": 30,
            "outline": "Perlihatkan kotak.",
            "asset_notes": "Karton.",
            "age_band": "3_5",
            "language": "id",
            "created_at": "2026-11-05T10:00:00Z",
            "updated_at": "2026-11-05T10:00:00Z",
        }

        # Simpan atomik
        kids_content.save_brief_atomic(self.test_dir, brief)
        file_path = self.test_dir / f"{brief_id}.json"
        self.assertTrue(file_path.is_file())

        # Baca kembali
        loaded = kids_content.read_brief(self.test_dir, brief_id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["title"], "Bentuk Kotak & Segitiga")
        self.assertEqual(loaded["revision"], 1)

        # Update revisi
        brief["revision"] = 2
        brief["title"] = "Bentuk Kotak & Segitiga (Update)"
        kids_content.save_brief_atomic(self.test_dir, brief)

        loaded_v2 = kids_content.read_brief(self.test_dir, brief_id)
        self.assertEqual(loaded_v2["revision"], 2)
        self.assertEqual(loaded_v2["title"], "Bentuk Kotak & Segitiga (Update)")

        # List briefs
        listing = kids_content.list_briefs(self.test_dir, page=1, page_size=10)
        self.assertEqual(listing["total"], 1)
        self.assertEqual(len(listing["briefs"]), 1)

        # Hapus brief
        deleted = kids_content.delete_brief(self.test_dir, brief_id)
        self.assertTrue(deleted)
        self.assertIsNone(kids_content.read_brief(self.test_dir, brief_id))

    def test_path_traversal_rejection(self):
        """Menolak ID dengan karakter path traversal atau format tidak valid."""
        for invalid_id in ("../../etc/passwd", "brief-1", "01234", "G" * 32, "a" * 31):
            with self.assertRaises(kids_content.KidsBriefError):
                kids_content.get_brief_path(self.test_dir, invalid_id)
            self.assertIsNone(kids_content.read_brief(self.test_dir, invalid_id))


class KidsStudioApiTest(unittest.TestCase):
    """Pengujian endpoint Flask untuk Studio Anak, brief OCC, dan ekspor."""

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="test_app_briefs_"))
        self.orig_briefs = app.view_functions.get("get_kids_briefs")
        # Arahkan KIDS_BRIEFS ke direktori uji sementara
        import app as app_module
        self.orig_kids_briefs_dir = app_module.KIDS_BRIEFS
        app_module.KIDS_BRIEFS = self.test_dir
        self.client = app.test_client()

    def tearDown(self):
        import app as app_module
        app_module.KIDS_BRIEFS = self.orig_kids_briefs_dir
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_get_kids_studio_page(self):
        """Halaman /kids mengembalikan 200 dengan informasi target 3–5 tahun Indonesia."""
        resp = self.client.get("/kids")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn("Studio Anak", html)
        self.assertIn("TARGET USIA 3–5 TAHUN · BAHASA INDONESIA", html)
        self.assertIn("Rekomendasi ide konten anak", html)
        self.assertIn("Brief konten anak", html)

    def test_get_existing_studios_still_work(self):
        """Halaman Studio Klip (/) dan Studio Global (/global) tetap berfungsi normal."""
        resp_local = self.client.get("/")
        self.assertEqual(resp_local.status_code, 200)
        self.assertIn("Studio klip", resp_local.get_data(as_text=True))
        self.assertIn("/kids", resp_local.get_data(as_text=True))

        resp_global = self.client.get("/global")
        self.assertEqual(resp_global.status_code, 200)
        self.assertIn("Studio Global", resp_global.get_data(as_text=True))
        self.assertIn("/kids", resp_global.get_data(as_text=True))

    def test_api_kids_ideas(self):
        """Endpoint /api/kids/ideas mengembalikan ide editorial dan filter kategori."""
        resp = self.client.get("/api/kids/ideas")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("ideas", data)
        self.assertGreaterEqual(len(data["ideas"]), 10)
        self.assertEqual(data["kind"], "editorial")

        # Filter kategori
        resp_warna = self.client.get("/api/kids/ideas?category=warna")
        self.assertEqual(resp_warna.status_code, 200)
        data_warna = resp_warna.get_json()
        self.assertTrue(all(i["category"] == "warna" for i in data_warna["ideas"]))

    def test_strict_payload_and_request_limit(self):
        for field, invalid in (("category", "unknown"), ("category", []),
                               ("target_duration", 30.9), ("target_duration", True),
                               ("target_duration", "30"), ("language", "en"),
                               ("age_band", "9_12"), ("idea_id", 123),
                               ("updated_at", "fake")):
            with self.subTest(field=field, value=invalid):
                response = self.client.post("/api/kids/briefs", json={"title": "Uji", field: invalid})
                self.assertEqual(response.status_code, 400)
        response = self.client.post("/api/kids/briefs", json={"title": "Uji", "extra": "x" * 33000})
        self.assertEqual(response.status_code, 413)
        created = self.client.post("/api/kids/briefs", json={"title": "Uji"}).get_json()["brief"]
        response = self.client.patch("/api/kids/briefs/" + created["brief_id"], json={"title": "Baru", "expected_revision": True})
        self.assertEqual(response.status_code, 400)

    def test_markup_is_preserved_as_literal_text_in_storage(self):
        payload = {"title": '<img src=x onerror="alert(1)">', "learning_goal": '<svg onload="alert(1)">'}
        response = self.client.post("/api/kids/briefs", json=payload)
        self.assertEqual(response.status_code, 201)
        brief = response.get_json()["brief"]
        loaded = self.client.get("/api/kids/briefs/" + brief["brief_id"]).get_json()["brief"]
        self.assertEqual(loaded["title"], payload["title"])
        self.assertEqual(loaded["learning_goal"], payload["learning_goal"])

    def test_api_kids_briefs_lifecycle_and_occ_conflict(self):
        """Siklus lengkap pembuatan, pembacaan, konflik revisi (409), pembaruan, dan penghapusan."""
        # 1. Buat brief baru
        create_payload = {
            "title": "Mengenal Suara Burung",
            "learning_goal": "Mencocokkan suara ciap dengan burung",
            "category": "hewan",
            "target_duration": 30,
            "outline": "Putar suara ciap -> tunjuk burung.",
            "asset_notes": "Audio burung dan foto burung.",
            "idea_id": "hewan-01",
        }
        res_create = self.client.post("/api/kids/briefs", json=create_payload)
        self.assertEqual(res_create.status_code, 201)
        created_brief = res_create.get_json()["brief"]
        brief_id = created_brief["brief_id"]
        self.assertEqual(created_brief["revision"], 1)
        self.assertEqual(created_brief["title"], "Mengenal Suara Burung")

        # 2. Baca detail
        res_get = self.client.get(f"/api/kids/briefs/{brief_id}")
        self.assertEqual(res_get.status_code, 200)
        self.assertEqual(res_get.get_json()["brief"]["title"], "Mengenal Suara Burung")

        # 3. Konflik Optimistic Concurrency (misal expected_revision tidak cocok)
        conflict_payload = {
            "expected_revision": 99,
            "title": "Judul Baru Yang Konflik",
        }
        res_conflict = self.client.patch(f"/api/kids/briefs/{brief_id}", json=conflict_payload)
        self.assertEqual(res_conflict.status_code, 409)
        conflict_data = res_conflict.get_json()
        self.assertTrue(conflict_data["conflict"])
        self.assertEqual(conflict_data["current_revision"], 1)
        self.assertEqual(conflict_data["server_brief"]["title"], "Mengenal Suara Burung")

        # 4. Update sukses dengan expected_revision yang sesuai
        valid_update = {
            "expected_revision": 1,
            "title": "Mengenal Suara Burung Kutilang",
            "target_duration": 45,
        }
        res_update = self.client.patch(f"/api/kids/briefs/{brief_id}", json=valid_update)
        self.assertEqual(res_update.status_code, 200)
        updated_brief = res_update.get_json()["brief"]
        self.assertEqual(updated_brief["revision"], 2)
        self.assertEqual(updated_brief["title"], "Mengenal Suara Burung Kutilang")
        self.assertEqual(updated_brief["target_duration"], 45)

        # 5. Ekspor TXT & JSON
        res_txt = self.client.get(f"/api/kids/briefs/{brief_id}/export?format=txt")
        self.assertEqual(res_txt.status_code, 200)
        self.assertEqual(res_txt.mimetype, "text/plain")
        self.assertIn("Mengenal Suara Burung Kutilang", res_txt.get_data(as_text=True))

        res_json = self.client.get(f"/api/kids/briefs/{brief_id}/export?format=json")
        self.assertEqual(res_json.status_code, 200)
        self.assertEqual(res_json.mimetype, "application/json")
        self.assertEqual(res_json.get_json()["brief_id"], brief_id)

        # 6. Hapus brief
        res_del = self.client.delete(f"/api/kids/briefs/{brief_id}")
        self.assertEqual(res_del.status_code, 200)
        self.assertTrue(res_del.get_json()["deleted"])

        # 7. Pastikan sudah tidak ditemukan (404)
        res_after = self.client.get(f"/api/kids/briefs/{brief_id}")
        self.assertEqual(res_after.status_code, 404)

    def test_brief_storage_ignored_by_history_scanner(self):
        """Memastikan folder kids-briefs tidak terbaca sebagai job oleh scanner history."""
        # Buat satu brief
        self.client.post("/api/kids/briefs", json={"title": "Brief Bebas", "category": "warna"})
        # Panggil endpoint history
        res_hist = self.client.get("/api/jobs")
        self.assertEqual(res_hist.status_code, 200)
        jobs = res_hist.get_json()["jobs"]
        # Pastikan tidak ada job dengan id folder kids-briefs
        for j in jobs:
            self.assertNotEqual(j.get("id"), "kids-briefs")


if __name__ == "__main__":
    unittest.main()
