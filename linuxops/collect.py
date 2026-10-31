"""Read host telemetry using Linux procfs and standard-library APIs."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import socket
import subprocess
import time


class MonitorError(RuntimeError):
    """Raised when telemetry cannot be collected safely and accurately."""


def cpu_counters(text: str) -> tuple[int, int]:
    """Return (total jiffies, idle jiffies) from a /proc/stat line."""
    line = text.splitlines()[0].split() if text.strip() else []
    if len(line) < 5 or line[0] != "cpu":
        raise MonitorError("Missing aggregate CPU data in /proc/stat")
    try:
        values = [int(x) for x in line[1:]]
    except ValueError as exc:
        raise MonitorError("Invalid CPU counters in /proc/stat") from exc
    if any(x < 0 for x in values):
        raise MonitorError("Negative CPU counters")
    total = sum(values)
    idle = values[3] + (values[4] if len(values) > 4 else 0)
    return total, idle


def cpu_usage(first: tuple[int, int], second: tuple[int, int]) -> float:
    total_delta = second[0] - first[0]
    idle_delta = second[1] - first[1]
    if total_delta <= 0 or idle_delta < 0 or idle_delta > total_delta:
        raise MonitorError("Invalid CPU sample interval or counters")
    return round(100 * (1 - idle_delta / total_delta), 2)


def memory_usage(text: str) -> float:
    values: dict[str, int] = {}
    for line in text.splitlines():
        tokens = line.replace(":", " ").split()
        if len(tokens) >= 2 and tokens[0] in {"MemTotal", "MemAvailable", "MemFree", "Buffers", "Cached"}:
            try:
                values[tokens[0]] = int(tokens[1])
            except ValueError as exc:
                raise MonitorError(f"Invalid /proc/meminfo field: {tokens[0]}") from exc
    total = values.get("MemTotal", 0)
    free = values.get("MemAvailable")
    if free is None and all(x in values for x in ("MemFree", "Buffers", "Cached")):
        free = values["MemFree"] + values["Buffers"] + values["Cached"]
    if total <= 0 or free is None or not 0 <= free <= total:
        raise MonitorError("Incomplete /proc/meminfo memory values")
    return round(100 * (total - free) / total, 2)


def network_totals(text: str) -> tuple[int, int]:
    received = sent = 0
    found = False
    for line in text.splitlines()[2:]:
        if ":" not in line:
            continue
        interface, counters = line.rsplit(":", 1)
        interface = interface.strip()
        if interface == "lo":
            continue
        cols = counters.split()
        if len(cols) < 16:
            continue
        try:
            rx, tx = int(cols[0]), int(cols[8])
        except ValueError as exc:
            raise MonitorError("Invalid /proc/net/dev network counters") from exc
        if rx < 0 or tx < 0:
            raise MonitorError("Negative /proc/net/dev network counters")
        received += rx
        sent += tx
        found = True
    if not found:
        return 0, 0
    return received, sent


def service_status(name: str) -> str:
    """Check a named systemd unit without invoking a shell."""
    if not name or len(name) > 120 or not all(c.isalnum() or c in "@._-" for c in name):
        raise ValueError("Invalid service name")
    try:
        result = subprocess.run(["systemctl", "is-active", "--", name], capture_output=True,
                                text=True, timeout=4, check=False)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return "unavailable"
    state = result.stdout.strip()
    return state if state in {"active", "inactive", "failed", "activating", "deactivating", "unknown"} else "unavailable"


def collect_linux(disk_path: str = "/", services: list[str] | None = None,
                  sample_seconds: float = 0.15, proc_root: str | Path = "/proc") -> dict:
    """Get a host snapshot, without root permission or writing to procfs."""
    if os.name != "posix" or not Path(proc_root, "stat").is_file():
        raise MonitorError("Linux procfs is required. Use `demo` on non-Linux systems.")
    if not 0.05 <= sample_seconds <= 5:
        raise ValueError("sample_seconds must be between 0.05 and 5")
    root = Path(proc_root)
    try:
        sample_a = cpu_counters((root / "stat").read_text(encoding="utf-8"))
        time.sleep(sample_seconds)
        sample_b = cpu_counters((root / "stat").read_text(encoding="utf-8"))
        memory = memory_usage((root / "meminfo").read_text(encoding="utf-8"))
        received, sent = network_totals((root / "net" / "dev").read_text(encoding="utf-8"))
        uptime = float((root / "uptime").read_text(encoding="utf-8").split()[0])
        load = os.getloadavg()
        usage = shutil.disk_usage(disk_path)
    except (OSError, IndexError, ValueError) as exc:
        raise MonitorError(f"Unable to read Linux metrics: {exc}") from exc
    if usage.total <= 0:
        raise MonitorError("Disk reports zero total bytes")
    return {
        "cpu_percent": cpu_usage(sample_a, sample_b),
        "memory_percent": memory,
        "disk_percent": round(100 * usage.used / usage.total, 2),
        "load_1m": round(load[0], 2), "load_5m": round(load[1], 2),
        "load_15m": round(load[2], 2), "uptime_seconds": round(uptime),
        "network_bytes_received": received,
        "network_bytes_sent": sent,
        "services": [{"name": name, "state": service_status(name)} for name in (services or [])],
    }


def hostname() -> str:
    return socket.gethostname().split(".")[0][:80]
