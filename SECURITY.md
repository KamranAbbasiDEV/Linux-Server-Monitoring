# Security and responsible operation

- No root credentials, passwords, API keys or AWS credentials are required for this project.
- Live telemetry is read-only. Use it only on servers or systems you are authorized to inspect.
- Monitoring results may reveal hostnames, service names and performance details. Keep real telemetry out of public repositories; `.gitignore` excludes JSONL history and log files.
- Do not commit production samples, customer logs, access tokens or secrets.
- The `services` config accepts a restricted name character set; `systemctl` is invoked using an argument list, **never a shell string**.
- JSONL logs are append-only; establish a rotation policy before long-term use. Do not configure unbounded storage on production systems.
- Demo samples are synthetic and do not indicate an actual service outage.
- The Dockerfile runs only synthetic demo mode to avoid implying it observes host-wide system metrics.
- The optional systemd timer runs under the current user. It does not require or grant elevated privileges.
- Filesystem location and user account security determine permissions on history files; store observations with appropriate access controls.
