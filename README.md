# Linux Server Monitoring — LinuxOps Agent

[![CI](https://github.com/KamranAbbasiDEV/linux-server-monitoring/actions/workflows/ci.yml/badge.svg)](https://github.com/KamranAbbasiDEV/linux-server-monitoring/actions/workflows/ci.yml)

An educational, **dependency-free Python and Bash monitoring toolkit** for Linux operations and cloud-support incident triage. It collects basic host metrics, evaluates warning/critical thresholds, checks systemd service state, writes a JSON Lines history, and generates an initial incident report.

> **Portfolio lab, not a production observability product.** All bundled demonstrations are **synthetic** and clearly labeled. Live collection reads only the Linux machine/container where the program runs; Docker does **not** grant host-wide visibility by default.

## Features

| Feature | Details |
| --- | --- |
| CPU | Two `/proc/stat` samples, measuring CPU utilization over a short interval |
| Memory | `/proc/meminfo` available-memory percentage |
| Disk | Configurable filesystem utilization using `shutil.disk_usage` |
| System load | Linux 1-, 5-, 15-minute load averages |
| Network | Total received/sent bytes for non-loopback interfaces |
| Services | Opt-in `systemctl is-active` checks, using subprocess without a shell |
| Thresholds | Configurable warning/critical percentages for CPU, memory and disk |
| History | Append-only structured JSONL observations |
| Reports | Markdown incident summary, peak usage, alerts and cautious next steps |
| Automation | Example systemd user service/timer and Bash wrapper |
| Tests | Offline unit tests with mocked IO and synthetic metrics; GitHub Actions CI |

Python 3.11+; **no runtime Python dependencies**.

## 30-second demonstration (Windows, macOS, or Linux)

From the repository root:

```bash
python -m linuxops demo
python -m linuxops demo --history out/history.jsonl --output out/latest.json
python -m linuxops report out/history.jsonl --output out/incident.md
```

The **offline demo** models high CPU, high memory and a failed `nginx` service to illustrate alert handling. No server is contacted and no privileges or AWS account are required.

## Monitor a Linux machine

```bash
python -m linuxops snapshot
python -m linuxops snapshot --history out/history.jsonl
python -m linuxops watch --interval 60 --count 3 --history out/history.jsonl
```

To monitor a Linux host's `nginx` service (replace the service name with one present on your machine):

```bash
python -m linuxops snapshot --config config.example.json
```

If `systemctl` cannot run, the service is marked `unavailable` and a **warning** is recorded. A failed or inactive service is **critical**. CPU utilization is sampled for 0.15 s and is noisy on short windows; choose alert thresholds carefully.

## Install a command

```bash
python -m pip install -e .
linuxops --help
linuxops demo
```

## Thresholds

`config.example.json` includes defaults of CPU 80/95%, memory 80/92%, and disk 80/92% (warning/critical). The `services` array is opt-in in normal operation. Copy the file and edit it to match your environment; any named services should exist on the target Linux machine.

Example alert output (excerpt from **synthetic** demonstration):

```json
{
  "overall_status": "critical",
  "source": "synthetic-demo",
  "alerts": [
    {"metric": "cpu_percent", "severity": "warning", "value": 91.5},
    {"metric": "memory_percent", "severity": "warning", "value": 84.3},
    {"metric": "service", "severity": "critical", "service": "nginx", "value": "failed"}
  ]
}
```

The example above is abbreviated; full output includes host, timestamp and evidence fields. See [example JSON snapshot](samples/example-snapshot.json) and [generated sample incident report](samples/EXAMPLE_INCIDENT_REPORT.md) for complete synthetic output.

## Schedule collection with systemd (optional)

This uses a **user-level** timer, not a privileged system service. First install the package for the same user account:

```bash
python3 -m pip install --user .
mkdir -p ~/.config/systemd/user
cp deploy/systemd/linuxops.* ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now linuxops.timer
systemctl --user list-timers linuxops.timer
```

The timer runs every five minutes and writes `~/.local/state/linuxops/history.jsonl`. On some distributions, Python/pip installation requires a virtual environment or distro package; adapt the `ExecStart` path to your chosen interpreter. **Do not enable a timer until you've inspected the files.** If user service collection should continue after logout, login lingering may need explicit administrator approval. For manual collection, use `scripts/quick-health.sh`.

## Docker (demo only)

```bash
docker build -t linuxops-monitor .
docker run --rm linuxops-monitor
```

The Docker image runs **synthetic demo data**. Even changing it to `snapshot` would measure container-visible metrics, not provide reliable bare-metal/VM host monitoring. Do not mount `/proc` from the host or grant privileged container access simply to run this portfolio example.

## Automated testing

```bash
python -m unittest discover -s tests -v
bash -n scripts/quick-health.sh
```

CI runs tests against Python 3.11, 3.12 and 3.13. It also runs a synthetic offline demo and incident-report generation. No cloud credentials, paid APIs or external monitoring services are necessary.

## Operational guidance

Read [runbooks](docs/RUNBOOKS.md), [architecture](docs/ARCHITECTURE.md), and [security considerations](SECURITY.md). Real incidents require verification of customer impact, service ownership, incident timeline and root cause. A threshold breach alone is not evidence of an outage.

## Limitations / roadmap

- Sampling is point-in-time; short CPU intervals can be noisy.
- Network counters are cumulative, **not throughput rates**.
- No alert notification integrations or persistent agent service are implemented.
- History files are append-only and should be rotated; reporting caps input at 15 MiB and 10,000 entries.
- No Windows/macOS live metrics; use the offline demo on those systems.
- Future work: Prometheus exporter, rate-of-change alerts, configurable log rotation, metrics graphs and authenticated integrations.

MIT licensed — see [LICENSE](LICENSE).
