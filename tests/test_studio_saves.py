"""Regression cases for save isolation, PIN validation and retries."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from riskmatch_v2.matching.ledger import Ledger
from riskmatch_v2.studio import dispatch
from riskmatch_v2.studio_saves import registry


class NamedSaves(TestCase):
    def test_pin_isolation_and_partial_resume(self):
        with TemporaryDirectory() as path:
            directory = Path(path)

            def api(action, **data):
                return dispatch(action, data, directory)

            with self.assertRaisesRegex(ValueError, "must match"):
                api("create_save", name="Tester A", pin="0427", confirmation="0428")
            self.assertEqual(api("list_saves"), [])
            a = api("create_save", name="Tester A", pin="0427", confirmation="0427")
            b = api("create_save", name="Tester B", pin="3180", confirmation="3180")
            rows = api("list_saves")
            self.assertEqual([row["name"] for row in rows], ["Tester A", "Tester B"])
            self.assertEqual(set(rows[0]), {"name", "id"})
            with self.assertRaisesRegex(ValueError, "Incorrect code"):
                api("unlock_save", id=rows[1]["id"], pin="0427")
            api("route", token=a["access"], answers={"C01": "yes"})
            self.assertEqual(api("resume", token=b["access"])["answers"], {})
            api("lock_save", token=a["access"])
            with self.assertRaisesRegex(ValueError, "Unlock your save"):
                api("resume", token=a["access"])
            unlocked = api("unlock_save", id=rows[0]["id"], pin="0427")
            self.assertEqual(
                api("resume", token=unlocked["access"])["answers"], {"C01": "yes"}
            )
            with registry(directory) as conn:
                raw = conn.execute(
                    "SELECT token, pin FROM saves WHERE id=?", (rows[0]["id"],)
                ).fetchone()
                self.assertNotEqual(raw["pin"], b"0427")
            with self.assertRaisesRegex(ValueError, "Unlock your save"):
                api("resume", token=raw["token"])

    def test_duplicate_names_and_retry_delay(self):
        with TemporaryDirectory() as path:
            directory = Path(path)
            old = Ledger.create(directory)
            dispatch(
                "create_save",
                {
                    "name": "Legacy",
                    "pin": "2200",
                    "confirmation": "2200",
                    "legacy_token": old.token,
                },
                directory,
            )
            with self.assertRaisesRegex(ValueError, "already in use"):
                dispatch(
                    "create_save",
                    {"name": "legacy", "pin": "2110", "confirmation": "2110"},
                    directory,
                )
            save = dispatch("list_saves", {}, directory)[0]["id"]
            with patch("riskmatch_v2.studio_saves.time.time", return_value=1000):
                for _ in range(4):
                    with self.assertRaisesRegex(ValueError, "Incorrect code"):
                        dispatch("unlock_save", {"id": save, "pin": "1000"}, directory)
                with self.assertRaisesRegex(ValueError, "Too many attempts"):
                    dispatch("unlock_save", {"id": save, "pin": "1000"}, directory)
                with self.assertRaisesRegex(ValueError, "Too many attempts"):
                    dispatch("unlock_save", {"id": save, "pin": "2200"}, directory)
            with patch("riskmatch_v2.studio_saves.time.time", return_value=1301):
                self.assertTrue(
                    dispatch("unlock_save", {"id": save, "pin": "2200"}, directory)[
                        "access"
                    ]
                )
