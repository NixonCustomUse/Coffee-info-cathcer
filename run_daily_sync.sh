#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

python3 coffee_radar.py --days 45 --limit 30 --min-score 2
python3 coffee_ai.py --input data/items.jsonl --output data/items.enriched.jsonl

if [ "$(date +%u)" = "1" ]; then
  python3 coffee_weekly.py --input data/items.enriched.jsonl --output-dir reports/weekly
  python3 coffee_notion_sync.py \
    --items data/items.enriched.jsonl \
    --limit 30 \
    --sync-weekly reports/weekly/latest.md \
    --skip-notion-if-unconfigured
else
  python3 coffee_notion_sync.py \
    --items data/items.enriched.jsonl \
    --limit 30 \
    --skip-notion-if-unconfigured
fi
