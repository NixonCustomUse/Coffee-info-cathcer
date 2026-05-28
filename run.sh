#!/bin/bash
set -euo pipefail
python3 coffee_radar.py --days 45 --min-score 2
python3 coffee_telegram.py --limit 10
