import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from kelip import app as module


class CaptionTests(unittest.TestCase):
    def test_caption_is_one_short_sentence_without_cta_or_hashtags(self):
        caption = module.make_caption("  Mulai dari kebiasaan kecil.\nJangan menunggu sempurna. ")
        self.assertEqual(caption,"Mulai dari kebiasaan kecil.")
        self.assertNotIn("#",caption)
        self.assertNotIn("komentar",caption)
        self.assertEqual(module.make_caption("A small habit makes a difference. Keep trying.",'global_en'),"A small habit makes a difference.")

    def test_long_transcript_is_bounded_and_empty_input_supported(self):
        caption = module.make_caption("percakapan " * 200)
        self.assertLessEqual(len(caption),121)
        self.assertLessEqual(len(caption.split()),16)
        self.assertTrue(caption.endswith("…"))
        self.assertTrue(module.make_caption(None))
        self.assertNotIn("\n",caption)

    def test_previous_generated_template_becomes_short(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(module,'DATA',Path(directory)), patch.object(module,'jobs',{}):
            folder=module.DATA/('b'*32);folder.mkdir()
            text='Mulai dari kebiasaan kecil. Jangan menunggu sempurna.'
            (folder/'job.json').write_text(json.dumps(dict(done=True,clips=[dict(text=text,caption=module.legacy_caption(text))])))
            self.assertEqual(module.read_job(folder.name)['clips'][0]['caption'],'Mulai dari kebiasaan kecil.')
            self.assertIn('Tulis di komentar',json.loads((folder/'job.json').read_text())['clips'][0]['caption'])

    def test_legacy_history_gets_caption_without_overwriting_saved_caption(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(module, "DATA", Path(directory)), patch.object(module, "jobs", {}):
            jid = "a" * 32; folder = module.DATA / jid; folder.mkdir()
            original = {"done":True, "clips":[{"text":"Transkrip lama"}, {"text":"Teks", "caption":"Caption tersimpan"}]}
            (folder / "job.json").write_text(json.dumps(original))
            job = module.app.test_client().get('/api/jobs/' + jid).json
            self.assertTrue(job["clips"][0]["caption"].startswith("Transkrip lama"))
            self.assertEqual(job["clips"][1]["caption"], "Caption tersimpan")


if __name__ == "__main__":
    unittest.main()
