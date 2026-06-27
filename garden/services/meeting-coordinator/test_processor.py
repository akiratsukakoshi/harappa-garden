#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("meeting_processor", ROOT / "processor.py")
processor = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(processor)


class MeetingCoordinatorTest(unittest.TestCase):
    def test_resolve_core_participants(self):
        self.assertEqual(processor.resolve_participants("少佐,ゆーじさん"), [
            "shotaro-shimura",
            "yuji-wada",
        ])

    def test_find_candidates_prefers_morning_then_afternoon(self):
        old_busy = processor._busy_events
        try:
            processor._busy_events = lambda start, end: []
            candidates = processor.find_candidates(2026, 7, 90, limit=3)
        finally:
            processor._busy_events = old_busy
        self.assertEqual([c["label"] for c in candidates], ["午前", "午後", "夜"])
        self.assertTrue(candidates[0]["start"].endswith("09:00:00+09:00"))

    def test_create_meeting_dry_run_does_not_write_state(self):
        old_busy = processor._busy_events
        with tempfile.TemporaryDirectory() as td:
            old_state = processor.STATE_PATH
            try:
                processor.STATE_PATH = Path(td) / "meetings.json"
                processor._busy_events = lambda start, end: []
                meeting = processor.create_meeting(
                    title="テスト会議",
                    meeting_type="spot",
                    participants=["akira-tsukakoshi", "shotaro-shimura"],
                    year=2026,
                    month=7,
                    duration_min=60,
                    proposer="akira-tsukakoshi",
                    confirmer="akira-tsukakoshi",
                    related_workflows=[],
                    dry_run=True,
                )
                self.assertEqual(meeting["status"], "open")
                self.assertFalse(processor.STATE_PATH.exists())
            finally:
                processor.STATE_PATH = old_state
                processor._busy_events = old_busy

    def test_add_availability_writes_state(self):
        with tempfile.TemporaryDirectory() as td:
            old_state = processor.STATE_PATH
            try:
                processor.STATE_PATH = Path(td) / "meetings.json"
                state = {
                    "meetings": {
                        "m1": {
                            "id": "m1",
                            "status": "open",
                            "meeting_type": "spot",
                            "availability": [],
                        }
                    }
                }
                processor.STATE_PATH.write_text(json.dumps(state), encoding="utf-8")
                entry = processor.add_availability("m1", "少佐", "AならOK")
                saved = json.loads(processor.STATE_PATH.read_text(encoding="utf-8"))
                self.assertEqual(entry["participant"], "shotaro-shimura")
                self.assertEqual(saved["meetings"]["m1"]["availability"][0]["text"], "AならOK")
            finally:
                processor.STATE_PATH = old_state


if __name__ == "__main__":
    unittest.main()
