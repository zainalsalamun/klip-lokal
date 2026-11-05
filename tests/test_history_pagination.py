import json
from pathlib import Path
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from collections import OrderedDict
import app as module


class PaginationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.patches = [patch.object(module, "DATA", Path(self.temp.name)), patch.object(module, "jobs", {}), patch.object(module, "history_cache", OrderedDict())]
        for item in self.patches: item.start()
        self.client = module.app.test_client()

    def tearDown(self):
        for item in reversed(self.patches): item.stop()
        self.temp.cleanup()

    def fixture(self, count):
        for i in range(count):
            jid = f"{i+1:032x}"; folder = module.DATA / jid; folder.mkdir()
            job = dict(id=jid, title=f"Video {i:04}", created_at=(datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(seconds=i)).isoformat(), done=True, status="Selesai", clips=[dict(text="sample")])
            if i % 5 == 0: job.update(error="fixture error", status="Gagal", clips=[])
            (folder / "job.json").write_text(json.dumps(job))
        return jid

    def test_thousand_records_search_paging_filter_and_cache(self):
        latest = self.fixture(1000)
        record = json.loads((module.DATA / latest / "job.json").read_text())
        record.update(done=False, status="Diproses")
        module.jobs[latest] = record
        with patch.object(module, "read_job", wraps=module.read_job) as reader:
            response = self.client.get('/api/jobs').json
            self.assertEqual(response["total"], 1000)
            self.assertEqual(response["total_pages"], 100)
            self.assertEqual(len(response["jobs"]), 10)
            self.assertEqual(response["jobs"][0]["id"], latest)
            self.assertEqual(response["active_job_id"], latest)
            first_reads = reader.call_count
            second = self.client.get('/api/jobs?page=2').json
            self.assertEqual(len(second["jobs"]), 10)
            self.assertFalse({j["id"] for j in response["jobs"]} & {j["id"] for j in second["jobs"]})
            self.assertEqual(reader.call_count, first_reads)
        searched = self.client.get('/api/jobs?q=video%200123').json
        self.assertEqual(searched["filtered_total"], 1)
        self.assertEqual(searched["jobs"][0]["title"], 'Video 0123')
        failed = self.client.get('/api/jobs?status=failed').json
        self.assertEqual(failed["filtered_total"], 200)
        self.assertTrue(all(job["error"] for job in failed["jobs"]))
        active = self.client.get('/api/jobs?status=processing').json
        self.assertEqual(active["filtered_total"], 1)
        self.assertEqual(active["jobs"][0]["id"], latest)
        empty = self.client.get('/api/jobs?q=not-found').json
        self.assertEqual(empty["jobs"], [])
        self.assertEqual(empty["total"], 1000)
        self.assertEqual(self.client.get('/api/jobs?page=999').json["page"], 100)
        self.assertLessEqual(len(module.history_cache), 1024)
        path = module.DATA / f"{2:032x}" / "job.json"
        changed = json.loads(path.read_text()); changed["title"] = "Changed title from external edit"
        path.write_text(json.dumps(changed))
        self.assertEqual(self.client.get('/api/jobs?q=Changed').json["filtered_total"], 1)

    def test_deleting_last_row_clamps_page_and_refreshes_totals(self):
        self.fixture(11)
        old = self.client.get('/api/jobs?page=2').json
        self.assertEqual(len(old["jobs"]), 1)
        jid = old["jobs"][0]["id"]
        self.assertEqual(self.client.delete('/api/jobs/' + jid).status_code, 200)
        remaining = self.client.get('/api/jobs?page=2').json
        self.assertEqual(remaining["page"], 1)
        self.assertEqual(remaining["total"], 10)
        self.assertEqual(len(remaining["jobs"]), 10)

    def test_invalid_pagination_rejected(self):
        for query in ['page=0', 'page=x', 'page_size=0', 'page_size=1000', 'status=unknown']:
            self.assertEqual(self.client.get('/api/jobs?' + query).status_code, 400)


if __name__ == '__main__': unittest.main()
