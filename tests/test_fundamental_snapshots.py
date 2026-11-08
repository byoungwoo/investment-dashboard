"""data/fundamentals/<TICKER>.json 파일 자체에 대한 검사.

값이 맞는지(= tests/test_fundamentals.py)가 아니라 **파일이 쓸 수 있는 모양인지**를 본다.
스냅샷을 에이전트나 사람이 손으로 쓰기 때문에, 필수 키 하나가 빠지면
show_fundamental_detail() 이 KeyError로 죽는다 — 화면이 아니라 여기서 먼저 막는다.
"""

import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from config import PORTFOLIO
from fundamentals import (
    FUNDAMENTAL_DETAILS,
    SNAPSHOT_DIR,
    STALE_AFTER_DAYS,
    load_snapshots,
    snapshot_age_days,
    staleness_note,
)

# show_fundamental_detail() 이 대괄호로 직접 읽는 키. 빠지면 패널이 죽는다.
REQUIRED = (
    "period",
    "updated",
    "badges",
    "flow_title",
    "flow",
    "financial_title",
    "financials",
    "financial_note",
    "status",
    "next_checks",
    "break_conditions",
    "source_label",
    "source_url",
)


class SnapshotFileTest(unittest.TestCase):
    def test_files_and_loaded_symbols_agree(self):
        """파일명이 심볼이다. 로더가 읽은 것과 디렉터리 내용이 같아야 한다."""
        on_disk = {path.stem for path in SNAPSHOT_DIR.glob("*.json")}
        self.assertEqual(on_disk, set(FUNDAMENTAL_DETAILS))
        self.assertTrue(on_disk, "스냅샷 파일이 하나도 없다")

    def test_filename_is_a_held_ticker(self):
        """오타 파일(IRENN.json)은 조용히 새 종목처럼 로드된다 — 여기서 잡는다."""
        for symbol in FUNDAMENTAL_DETAILS:
            self.assertIn(symbol, PORTFOLIO, symbol)
            self.assertEqual(symbol, symbol.upper(), symbol)

    def test_every_snapshot_has_every_required_key(self):
        for symbol, detail in FUNDAMENTAL_DETAILS.items():
            for key in REQUIRED:
                self.assertIn(key, detail, f"{symbol}: {key} 없음")

    def test_source_is_a_real_link(self):
        """출처 없는 수치는 지어낸 수치와 구별되지 않는다 (ADR-0003)."""
        for symbol, detail in FUNDAMENTAL_DETAILS.items():
            self.assertTrue(detail["source_url"].startswith("https://"), symbol)
            self.assertTrue(detail["source_label"].strip(), symbol)

    def test_updated_is_a_parseable_date(self):
        """신선도 경고가 이 값을 날짜로 읽는다. 'Q1 FY27' 같은 걸 넣으면 경고가 죽는다."""
        for symbol, detail in FUNDAMENTAL_DETAILS.items():
            self.assertEqual(
                detail["updated"],
                date.fromisoformat(detail["updated"]).isoformat(),
                symbol,
            )

    def test_status_block_is_renderable(self):
        for symbol, detail in FUNDAMENTAL_DETAILS.items():
            for key in ("emoji", "label", "tone"):
                self.assertIn(key, detail["status"], f"{symbol}: status.{key} 없음")

    def test_checklists_are_non_empty_lists(self):
        for symbol, detail in FUNDAMENTAL_DETAILS.items():
            for key in ("next_checks", "break_conditions"):
                self.assertIsInstance(detail[key], list, f"{symbol}: {key}")
                self.assertTrue(detail[key], f"{symbol}: {key} 가 비어 있다")


class LoaderTest(unittest.TestCase):
    def test_loads_by_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "AAA.json").write_text(json.dumps({"period": "Q1"}), encoding="utf-8")
            Path(tmp, "BBB.json").write_text(json.dumps({"period": "Q2"}), encoding="utf-8")
            loaded = load_snapshots(tmp)
        self.assertEqual({"AAA", "BBB"}, set(loaded))
        self.assertEqual("Q1", loaded["AAA"]["period"])

    def test_empty_directory_is_not_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual({}, load_snapshots(tmp))


class StalenessTest(unittest.TestCase):
    def test_fresh_snapshot_shows_no_warning(self):
        detail = {"updated": "2026-11-05"}
        self.assertEqual(3, snapshot_age_days(detail, date(2026, 11, 8)))
        self.assertIsNone(staleness_note(detail, date(2026, 11, 8)))

    def test_old_snapshot_warns_with_its_own_date(self):
        detail = {"updated": "2026-07-16"}
        note = staleness_note(detail, date(2026, 11, 8))
        self.assertIsNotNone(note)
        self.assertIn("2026-07-16", note)
        self.assertIn("115일", note)

    def test_boundary_is_stale_after_the_threshold(self):
        updated = date(2026, 1, 1)
        detail = {"updated": updated.isoformat()}
        self.assertIsNone(staleness_note(detail, updated + timedelta(days=STALE_AFTER_DAYS - 1)))
        self.assertIsNotNone(staleness_note(detail, updated + timedelta(days=STALE_AFTER_DAYS)))

    def test_unparseable_date_never_crashes_the_panel(self):
        """'Q1 FY2027' 처럼 날짜가 아닌 값이 들어와도 패널은 떠야 한다."""
        for bad in ({"updated": "Q1 FY2027"}, {"updated": None}, {}):
            self.assertIsNone(snapshot_age_days(bad, date(2026, 11, 8)), bad)
            self.assertIsNone(staleness_note(bad, date(2026, 11, 8)), bad)
