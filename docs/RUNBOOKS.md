# LinuxOps — Technical Support Runbooks

The program is for measurement and triage, not unattended remediation. Follow your organization's incident management process before changing production systems.

## CPU warning or critical threshold

1. Confirm repeat readings with `python -m linuxops snapshot` and compare with workload baselines.
2. Check `uptime`, `top -o %CPU`, and `ps aux --sort=-%cpu | head` on an authorized machine.
3. Compare with deployments, scheduled jobs, background queues and CloudWatch or other existing monitoring.
4. Correlate suspected issues with application latency/error rates; CPU load alone does not prove customer impact.
5. If escalating, document timestamps, host, process names, impact and immediate actions.

## Memory pressure

1. Confirm `free -h`, `/proc/meminfo`, and repeated monitoring readings.
2. Identify large processes via `ps aux --sort=-%mem | head`.
3. Inspect application logs for out-of-memory kills (`journalctl -k`) if authorized.
4. Avoid restarting processes without change authorization; preserve diagnostic evidence first.

## Disk usage

1. Check `df -h` and correct mounted filesystem.
2. Check `du -xhd1` for the affected tree; consider retention and ownership.
3. Verify logs, backups, release artifacts and temporary files.
4. Avoid deleting files blindly; follow backup, retention and rollback policy.

## Service not active

1. Confirm the unit name: `systemctl status nginx` (replace as appropriate).
2. Review `journalctl -u nginx -n 100 --no-pager` for errors.
3. Check dependencies, config syntax, resource exhaustion and recent changes.
4. Confirm whether the monitoring user can contact systemd; `unavailable` can indicate an environment issue, not a failed service.
5. Escalate with logs, reproduction steps and a proposed safe recovery procedure.

## Incident ticket template

- Date/time (UTC):
- Host or system:
- Service owner:
- Customer impact: **not confirmed until checked**
- Evidence / metrics:
- Recent changes:
- Next troubleshooting action:
- Escalation / communications:
- Verified root cause (only after investigation):
- Post-incident action:
