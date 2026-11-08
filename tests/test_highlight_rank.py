import json
import unittest
from unittest.mock import patch

from kelip import highlight_rank as rank


class HighlightRankTests(unittest.TestCase):
    shortlist = [
        {"start": 0, "end": 10, "text": "Kutipan pertama."},
        {"start": 20, "end": 30, "text": "Kutipan kedua."},
        {"start": 40, "end": 50, "text": "Kutipan ketiga."},
    ]

    def setUp(self):
        self.tags = patch.object(rank.ollama, "ensure_runtime",
                                 return_value={"models": [{"name": rank.ollama.MODEL}]})
        self.tags.start()
        self.addCleanup(self.tags.stop)

    def test_ranks_existing_ids_without_modifying_timestamps_or_input(self):
        picks = [{"id": 3, "reason": "insight"}, {"id": 1, "reason": "hook"}]
        with patch.object(rank.ollama, "request", return_value=self.response(picks)) as request:
            result = rank.rank_candidates(self.shortlist, 2, "general")
        self.assertEqual(result, [
            {**self.shortlist[2], "highlight_reason": "insight"},
            {**self.shortlist[0], "highlight_reason": "hook"},
        ])
        self.assertNotIn("highlight_reason", self.shortlist[0])
        self.assertEqual(request.call_args.args[0], "/api/chat")
        self.assertEqual(request.call_args.args[1]["keep_alive"], 0)

    def test_invalid_output_returns_fallback_and_releases_lock(self):
        for invalid in (True, 9, 1, "2"):
            with self.subTest(invalid=invalid):
                picks = [{"id": 1, "reason": "story"}, {"id": invalid, "reason": "hook"}]
                with patch.object(rank.ollama, "request", return_value=self.response(picks)):
                    self.assertIsNone(rank.rank_candidates(self.shortlist, 2, "general"))
                self.assertFalse(rank.ollama.inference_lock.locked())
        with patch.object(rank.ollama, "request", side_effect=TimeoutError):
            self.assertIsNone(rank.rank_candidates(self.shortlist, 2, "general"))
        self.assertFalse(rank.ollama.inference_lock.locked())

    @staticmethod
    def response(picks):
        return {"message": {"content": json.dumps({"picks": picks})}}
