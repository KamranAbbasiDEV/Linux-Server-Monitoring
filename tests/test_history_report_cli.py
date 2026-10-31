import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
import io

from linuxops.cli import main
from linuxops.history import read_history, save_snapshot
from linuxops.report import build_report


class WorkflowTests(unittest.TestCase):
    def test_demo_prints_critical_snapshot(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            rc = main(["demo"])
        self.assertEqual(rc, 0)
        data = json.loads(stdout.getvalue())
        self.assertEqual(data["source"], "synthetic-demo")
        self.assertEqual(data["overall_status"], "critical")
        self.assertEqual(len(data["alerts"]), 3)

    def test_demo_saves_json_and_history(self):
        with tempfile.TemporaryDirectory() as d:
            out, history = str(Path(d) / "latest.json"), str(Path(d) / "metrics.jsonl")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(["demo", "--output", out, "--history", history]), 0)
            saved = json.loads(Path(out).read_text(encoding="utf-8"))
            rows, skipped = read_history(history)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["overall_status"], saved["overall_status"])
            self.assertEqual(skipped, 0)

    def test_report_from_history(self):
        with tempfile.TemporaryDirectory() as d:
            source, dest = str(Path(d) / "history.jsonl"), str(Path(d) / "incident.md")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(["demo", "--history", source]), 0)
                self.assertEqual(main(["report", source, "--output", dest]), 0)
            report = Path(dest).read_text(encoding="utf-8")
            self.assertIn("Monitoring Incident Summary", report)
            self.assertIn("Service nginx state", report)
            self.assertIn("Root cause", report)

    def test_history_skips_malformed(self):
        with tempfile.TemporaryDirectory() as d:
            file = Path(d) / "history.jsonl"
            file.write_text('not-json\n{"metrics": {}, "alerts": []}\n', encoding="utf-8")
            rows, skipped = read_history(str(file))
            self.assertEqual((len(rows), skipped), (1, 1))

    def test_history_limits(self):
        with tempfile.TemporaryDirectory() as d:
            file = Path(d) / "history.jsonl"
            save_snapshot({"metrics": {}, "alerts": []}, str(file))
            with self.assertRaises(ValueError):
                read_history(str(file), limit=10001)

    def test_empty_report_rejected(self):
        with self.assertRaises(ValueError):
            build_report([])

    def test_invalid_config_file_cli_fails_without_traceback(self):
        with tempfile.TemporaryDirectory() as d:
            bad_config = Path(d) / "config.json"
            bad_config.write_text('{"bad": 1}', encoding="utf-8")
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                self.assertEqual(main(["demo", "--config", str(bad_config)]), 2)
            self.assertIn("Error:", stderr.getvalue())
            self.assertNotIn("Traceback", stderr.getvalue())

    def test_watch_bad_interval_rejected(self):
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            self.assertEqual(main(["watch", "--interval", "1", "--count", "1"]), 2)
            self.assertIn("interval", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
