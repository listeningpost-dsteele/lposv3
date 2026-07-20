#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if command -v python3 >/dev/null 2>&1; then
  exec python3 "$ROOT/install.py" "$@"
elif command -v python >/dev/null 2>&1; then
  exec python "$ROOT/install.py" "$@"
else
  echo "ERROR: Python 3.11 or later is required." >&2
  exit 2
fi
