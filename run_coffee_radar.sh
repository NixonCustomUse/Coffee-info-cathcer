#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
python3 coffee_radar.py --days 45 --limit 30 --min-score 2
