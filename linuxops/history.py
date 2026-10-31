"""Append-only JSON Lines history and bounded offline reading."""
from __future__ import annotations

import json
from pathlib import Path

MAX_HISTORY_BYTES = 15 * 1024 * 1024


def save_snapshot(snapshot: dict, path: str) -> None:
    file = Path(path).expanduser()
    file.parent.mkdir(parents=True, exist_ok=True)
    with file.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(snapshot, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n")


def read_history(path: str, limit: int = 10000) -> tuple[list[dict], int]:
    file = Path(path).expanduser()
    if not 1 <= limit <= 10000:
        raise ValueError("History limit must be between 1 and 10000")
    if file.stat().st_size > MAX_HISTORY_BYTES:
        raise ValueError("History exceeds 15 MiB; rotate or archive old records first")
    entries, ignored = [], 0
    with file.open("r", encoding="utf-8") as stream:
        for line in stream:
            if len(entries) >= limit:
                break
            try:
                item = json.loads(line)
                if not isinstance(item, dict) or not isinstance(item.get("metrics"), dict) or not isinstance(item.get("alerts"), list):
                    raise ValueError("Invalid snapshot record")
                entries.append(item)
            except (json.JSONDecodeError, ValueError):
                ignored += 1
    return entries, ignored
