#!/usr/bin/env bash
set -euo pipefail

exec uv run --no-sync python scripts/start.py
