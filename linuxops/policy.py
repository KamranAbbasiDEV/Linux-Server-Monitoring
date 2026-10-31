"""Configuration validation and threshold-based evaluation."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
METRICS = ("cpu_percent", "memory_percent", "disk_percent")
DEFAULT_CONFIG = {
    "disk_path": "/",
    "services": [],
    "thresholds": {
        "cpu_percent": {"warning": 80, "critical": 95},
        "memory_percent": {"warning": 80, "critical": 92},
        "disk_percent": {"warning": 80, "critical": 92},
    },
}


def validate_config(config: dict) -> dict:
    if not isinstance(config, dict):
        raise ValueError("Config must be a JSON object")
    if set(config) != {"disk_path", "services", "thresholds"}:
        raise ValueError("Config keys must be disk_path, services, and thresholds")
    if not isinstance(config["disk_path"], str) or not config["disk_path"].startswith("/"):
        raise ValueError("disk_path must be an absolute Linux path")
    services = config["services"]
    if not isinstance(services, list) or len(services) > 30:
        raise ValueError("services must be a list containing at most 30 names")
    for service in services:
        if not isinstance(service, str) or not 1 <= len(service) <= 120 or not all(c.isalnum() or c in "@._-" for c in service):
            raise ValueError("Invalid service name; only letters, numbers, @ . _ and - are allowed")
    if len(set(services)) != len(services):
        raise ValueError("Duplicate service name")
    thresholds = config["thresholds"]
    if not isinstance(thresholds, dict) or set(thresholds) != set(METRICS):
        raise ValueError("Thresholds must cover cpu_percent, memory_percent and disk_percent")
    for name in METRICS:
        limits = thresholds[name]
        if not isinstance(limits, dict) or set(limits) != {"warning", "critical"}:
            raise ValueError(f"{name} requires warning and critical thresholds")
        warning, critical = limits["warning"], limits["critical"]
        if type(warning) not in (int, float) or type(critical) not in (int, float) or not 0 < warning < critical <= 100:
            raise ValueError(f"{name}: require 0 < warning < critical <= 100")
    return config


def load_config(path: str | None) -> dict:
    # Round-trip avoids mutating global defaults in caller code.
    base = json.loads(json.dumps(DEFAULT_CONFIG))
    if not path:
        return base
    return validate_config(json.loads(Path(path).read_text(encoding="utf-8")))


def evaluate(metrics: dict[str, Any], config: dict, *, source: str, host: str) -> dict:
    validate_config(config)
    alerts: list[dict] = []
    for name in METRICS:
        value = metrics.get(name)
        if type(value) not in (int, float) or not 0 <= value <= 100:
            raise ValueError(f"{name} must be numeric in range 0..100")
        limits = config["thresholds"][name]
        level = "critical" if value >= limits["critical"] else "warning" if value >= limits["warning"] else None
        if level:
            alerts.append({"metric": name, "severity": level, "value": value,
                           "threshold": limits[level], "message": f"{name} at {value}% (>= {limits[level]}% {level} threshold)"})
    services = metrics.get("services", [])
    if not isinstance(services, list):
        raise ValueError("services metric must be a list")
    for svc in services:
        if not isinstance(svc, dict) or not isinstance(svc.get("name"), str) or not isinstance(svc.get("state"), str):
            raise ValueError("Invalid services metric")
        if svc["state"] != "active":
            severity = "warning" if svc["state"] in {"activating", "deactivating", "unavailable", "unknown"} else "critical"
            alerts.append({"metric": "service", "severity": severity, "service": svc["name"],
                           "value": svc["state"], "message": f"Service {svc['name']} state: {svc['state']}"})
    overall = "critical" if any(a["severity"] == "critical" for a in alerts) else "warning" if alerts else "healthy"
    return {"schema_version": SCHEMA_VERSION,
            "collected_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": source, "hostname": host, "overall_status": overall,
            "metrics": metrics, "alerts": alerts}
