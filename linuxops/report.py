"""Conservative Markdown incident summary from historical observations."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone


def _safe(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ").replace("`", "'")[:180]


def build_report(entries: list[dict], ignored: int = 0) -> str:
    if not entries:
        raise ValueError("No valid snapshots available for reporting")
    statuses = Counter(str(e.get("overall_status", "unknown")) for e in entries)
    alerts = [a for e in entries for a in e.get("alerts", []) if isinstance(a, dict)]
    severity = Counter(str(a.get("severity", "unknown")) for a in alerts)
    lines = ["# LinuxOps — Monitoring Incident Summary", "",
             f"- **Generated (UTC):** {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
             f"- **Source(s):** {', '.join(sorted({_safe(e.get('source', 'unknown')) for e in entries}))}",
             f"- **Samples reviewed:** {len(entries)}",
             f"- **Unparseable records skipped:** {ignored}",
             f"- **First sample:** {_safe(entries[0].get('collected_at_utc', 'unknown'))}",
             f"- **Last sample:** {_safe(entries[-1].get('collected_at_utc', 'unknown'))}",
             "", "## Health distribution", "",
             "| Status | Count |", "| --- | ---: |"]
    for name in ("healthy", "warning", "critical", "unknown"):
        if statuses[name]:
            lines.append(f"| {name} | {statuses[name]} |")
    lines += ["", "## Peak observed utilization", "",
              "| Metric | Peak |", "| --- | ---: |"]
    for name in ("cpu_percent", "memory_percent", "disk_percent"):
        values = [e["metrics"].get(name) for e in entries]
        numeric = [v for v in values if type(v) in (int, float) and 0 <= v <= 100]
        lines.append(f"| {_safe(name)} | {max(numeric):.2f}% |" if numeric else f"| {_safe(name)} | No data |")
    lines += ["", "## Alerts observed", "",
              f"- **Critical alert observations:** {severity['critical']}",
              f"- **Warning alert observations:** {severity['warning']}",
              "", "| Signal | Severity | Observed |", "| --- | --- | --- |"]
    for alert in alerts[:25]:
        lines.append(f"| {_safe(alert.get('metric', 'unknown'))} | {_safe(alert.get('severity', 'unknown'))} | {_safe(alert.get('message', 'no detail'))} |")
    if not alerts:
        lines.append("| None | — | No threshold alerts in the supplied samples |")
    if len(alerts) > 25:
        lines.append(f"\n*Showing first 25 of {len(alerts)} alert observations.*")
    lines += ["", "## Incident assessment", "",
              "- **Customer impact:** Unconfirmed; require validation against service health and user reports.",
              "- **Root cause:** Not yet verified. Threshold observations are evidence, not diagnosis.",
              "", "## Suggested operator follow-up", "",
              "1. Verify whether sampled conditions persist and affect actual users.",
              "2. For CPU or memory alerts, inspect top processes and recent workload changes.",
              "3. For disk alerts, inspect filesystem capacity and growth before removing data.",
              "4. For service alerts, inspect systemd status and recent journal logs.",
              "5. Record impact, escalation owner, timeline, mitigation and customer updates.",
              "", "> Threshold breaches do not prove customer impact or establish root cause.", ""]
    return "\n".join(lines)
