# Coffee Info Catcher

Coffee Info Catcher（原 Coffee Radar）是一個咖啡資訊自動收集器。從 RSS feed、公開頁面、Crossref 與 Europe PMC 抓取資料，分類為 6 大類別，輸出 Markdown 報告與 JSONL。

**零依賴** — 僅使用 Python 標準函式庫，無需 `pip install`。

## 快速開始

```bash
python3 coffee_radar.py
```

預設輸出：`reports/latest.md`（摘要報告）、`data/items.jsonl`（原始資料）。

常用參數：

```bash
python3 coffee_radar.py --days 30 --limit 20 --min-score 3
```

- `--days`：保留最近幾天的內容
- `--limit`：報告最多顯示幾筆
- `--min-score`：關鍵字門檻，越高越嚴格

## 完整流程

```bash
./run_daily_sync.sh
```

順序執行：
1. `coffee_radar.py` — 收集資料（`data/items.jsonl`）
2. `coffee_ai.py` — 產生中文摘要（`data/items.enriched.jsonl`）
3. `coffee_notion_sync.py` — 同步到 Notion（每週一額外產生週報）

## 環境變數

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `OPENROUTER_API_KEY` | `""` | 主要 LLM key（無則降級 OpenAI） |
| `OPENAI_API_KEY` | `""` | 降級備援 |
| `NOTION_TOKEN` | `""` | |
| `OPENROUTER_MODEL` | `openrouter/free` | |
| `NOTION_ARTICLES_DATABASE_ID` | 來自 `notion_config.json` | 環境變數優先 |

Notion 資料庫 ID 優先讀取環境變數，未設定時讀取 `notion_config.json`。

## 測試

```bash
python3 -m unittest tests/test_coffee_radar.py
python3 -m unittest tests.test_coffee_radar.CoffeeRadarTest.test_parse_feed_and_classify
```

## 其他操作

```bash
# 僅產生中文摘要（使用本地規則，不呼叫 API）
python3 coffee_ai.py --input data/items.jsonl --no-ai

# 手動產生週報
python3 coffee_weekly.py --input data/items.enriched.jsonl

# Notion 同步乾跑
python3 coffee_notion_sync.py --items data/items.enriched.jsonl --dry-run

# 產生 HTML 儀表板
python3 generate_html.py --input data/items.enriched.jsonl --output reports/report.html
```

## 資料來源

20 個來源（RSS / 頁面 / 學術 API），透過 `sources.json` 的 `enabled` 欄位開關。來源類型：`feed`（RSS/Atom）、`page`（抽取頁面連結）、`crossref`、`europe_pmc`（含專利）。
