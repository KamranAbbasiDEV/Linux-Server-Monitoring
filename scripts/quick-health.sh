#!/usr/bin/env bash
set -euo pipefail
if [[ ! -r /proc/stat ]]; then
  echo "Linux procfs is required for live monitoring; use: python3 -m linuxops demo" >&2
  exit 2
fi
exec python3 -m linuxops snapshot "$@"
