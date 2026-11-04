#!/usr/bin/env bash
# PD-M4-MAC-STUB-01 — shell entry for macOS packaging stub.
# Delegates to build_macos_stub.py (NOT RUN on non-Darwin; never forge PASS).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$ROOT/build_macos_stub.py" "$@"
