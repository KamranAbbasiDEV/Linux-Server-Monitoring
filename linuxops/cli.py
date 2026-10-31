"""LinuxOps Monitoring Agent CLI. No privileged access or AWS credentials required."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from importlib.resources import files
import sys
import time

from .collect import MonitorError, collect_linux, hostname
from .history import read_history, save_snapshot
from .policy import evaluate, load_config
from .report import build_report


def _serialize(obj: dict) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + "\n"


def _write(content: str, output: str | None) -> None:
    if output:
        dest = Path(output).expanduser()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
    else:
        print(content, end="")


def _snapshot(mode: str, config: dict, sample: str | None = None) -> dict:
    if mode == "demo":
        sample_path = Path(sample) if sample else files("linuxops").joinpath("demo-metrics.json")
        metrics = json.loads(sample_path.read_text(encoding="utf-8"))
        return evaluate(metrics, config, source="synthetic-demo", host="demo-linux-host")
    metrics = collect_linux(disk_path=config["disk_path"], services=config["services"])
    return evaluate(metrics, config, source="linux-procfs", host=hostname())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="linuxops", description="Linux monitoring, threshold alerts, and incident reporting")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (("snapshot", "Capture one live Linux host snapshot"),
                            ("demo", "Evaluate synthetic, offline sample metrics"),
                            ("watch", "Capture periodic live snapshots (Ctrl-C to exit)")):
        cmd = sub.add_parser(name, help=help_text)
        cmd.add_argument("--config", help="JSON thresholds and monitored services")
        cmd.add_argument("--history", help="Append snapshots to JSONL file")
        cmd.add_argument("--output", help="Save latest JSON snapshot to file")
        if name == "demo":
            cmd.add_argument("--sample", help="Optional metrics JSON file for an offline demo")
        if name == "watch":
            cmd.add_argument("--interval", type=float, default=60, help="Seconds between samples, minimum 5")
            cmd.add_argument("--count", type=int, default=0, help="Number of snapshots, 0 = continuous")
    report = sub.add_parser("report", help="Generate Markdown report from JSONL history")
    report.add_argument("history", help="Path to observations.jsonl")
    report.add_argument("--output", help="Destination Markdown file")
    report.add_argument("--limit", type=int, default=10000, help="Maximum samples examined")
    args = parser.parse_args(argv)
    try:
        if args.command == "report":
            rows, skipped = read_history(args.history, args.limit)
            _write(build_report(rows, skipped), args.output)
            return 0
        cfg = load_config(args.config)
        if args.command == "watch" and (args.interval < 5 or args.count < 0):
            raise ValueError("watch interval must be >= 5 seconds and count >= 0")
        cycles = args.count if args.command == "watch" and args.count else None if args.command == "watch" else 1
        iteration = 0
        while cycles is None or iteration < cycles:
            result = _snapshot("demo" if args.command == "demo" else "snapshot", cfg, getattr(args, "sample", None))
            _write(_serialize(result), args.output)
            if args.history:
                save_snapshot(result, args.history)
            iteration += 1
            if args.command != "watch":
                break
            if cycles is None or iteration < cycles:
                time.sleep(args.interval)
        # Warnings and critical alerts are data, not command failures.
        # An external scheduler can inspect JSON's overall_status if alerting is desired.
        return 0
    except (MonitorError, OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130
