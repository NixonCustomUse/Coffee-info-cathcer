# Coffee Info Catcher

Coffee Info Catcher（原 Coffee Radar）是一個咖啡資訊自動收集器。從 RSS feed、公開頁面、Crossref 與 Europe PMC 抓取資料，分類為 6 大類別，輸出 Markdown 報告與 JSONL。

**零依賴** — 僅使用 Python 標準函式庫，無需 `pip install`。

## 快速開始

```bash
./run.sh
# 或直接：python3 coffee_radar.py
```

預設輸出：`reports/latest.md`（摘要報告）、`data/items.jsonl`（原始資料，含中文摘要）。

常用參數：

```bash
python3 coffee_radar.py --days 30 --min-score 3
```

- `--days`：保留最近幾天的內容
- `--limit`：報告最多顯示幾筆
- `--min-score`：關鍵字門檻，越高越嚴格
- `--no-enrich`：不產生中文摘要

## Pipeline

```bash
python3 coffee_radar.py --days 45 --min-score 2
```

單一腳本完成：收集 → 分類 → 中文摘要 → Markdown 報告 + 分眾報告。

## 測試

```bash
python3 -m unittest discover -s tests
```

## 資料來源

20 個來源（RSS / 頁面 / 學術 API），透過 `sources.json` 的 `enabled` 欄位開關。來源類型：`feed`（RSS/Atom）、`page`（抽取頁面連結）、`crossref`、`europe_pmc`（含專利）。
