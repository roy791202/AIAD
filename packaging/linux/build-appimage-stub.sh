#!/usr/bin/env bash
# PD-M4-LINUX-STUB-01 — shell entry for Linux AppImage stub.
# Delegates to build-linux-stub.py (NOT RUN on non-Linux; never forge PASS).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$ROOT/build_linux_stub.py" "$@"
