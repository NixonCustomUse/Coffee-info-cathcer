#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

python3 coffee_radar.py --days 45 --limit 30 --min-score 2
python3 coffee_ai.py --input data/items.jsonl --output data/items.enriched.jsonl

python3 coffee_telegram.py --input data/items.enriched.jsonl --limit 10
