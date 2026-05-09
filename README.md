# Coffee Radar

Coffee Radar 是一個咖啡資訊自動收集器的 MVP。它會從 RSS feed 與公開頁面抓取資料，依照關鍵字把內容分成「農場/產地」「種植/氣候」「處理法/後製」「烘焙/萃取技術」「設備/自動化」「市場/價格」等類別，最後輸出 Markdown 報告與 JSONL 原始資料。

## 快速開始

```bash
python3 coffee_radar.py
```

預設輸出：

- `reports/latest.md`: 可閱讀的中文摘要報告
- `data/items.jsonl`: 後續可匯入資料庫或試算表的原始資料

常用參數：

```bash
python3 coffee_radar.py --days 30 --limit 20 --min-score 3
```

- `--days`: 只保留最近幾天的內容；日期缺失的項目會保留
- `--limit`: Markdown 報告最多顯示幾筆
- `--min-score`: 關鍵字門檻，數字越高越嚴格

執行收集時，終端機會顯示每個來源的進度條與狀態（OK/FAIL）。

完整流程建議直接使用一鍵腳本：

```bash
./run_daily_sync.sh
```

`run_coffee_radar.sh` 僅保留給除錯或單獨重跑資料收集時使用。

## 同步到 Notion

這個專案現在有完整同步流程：

```bash
./run_daily_sync.sh
```

流程會做四件事：

- 收集最近咖啡資訊
- 產生中文摘要，優先使用 OpenAI API；沒有 API key 時使用本地規則摘要
- 用本地 SQLite 記錄已同步網址，避免重複匯入同一篇文章
- 匯入 Notion；每週一額外產生週報文章並同步到 Coffee Radar 主頁

需要的環境變數：

```bash
export OPENAI_API_KEY=""
export NOTION_TOKEN=""
```

可選設定：

```bash
export OPENAI_MODEL=""
```

Notion 頁面與資料庫 ID 放在 `notion_config.json`。目前已指向：

- Coffee Radar 主頁
- Coffee Radar Articles
- Coffee Radar Sources

本專案只保留一份 `notion_config.json`，請直接填入自己的 Notion 資源 ID。

## 每週自動執行

可用 macOS/Linux 的排程工具每週跑一次 `run_daily_sync.sh`。如果用 Codex 自動化，已可設定每週固定時間執行。

## 每週文章

手動產生週報：

```bash
python3 coffee_weekly.py --input data/items.enriched.jsonl
```

輸出位置：

- `reports/weekly/latest.md`
- `reports/weekly/YYYY-Www.md`

週報會整理：

- 這個星期發生了什麼
- 有什麼新的研究
- 有什麼新的技術、設備或產品
- 市場與商業模式有哪些變化
- 下週應該追蹤什麼問題

## 資料來源

目前來源放在 `sources.json`，可以直接增減：

- Daily Coffee News
- World Coffee Research
- Specialty Coffee Association
- Coffee Science Foundation
- Perfect Daily Grind
- Sprudge
- Global Coffee Report
- International Coffee Organization

如果某個網站沒有 RSS，可以把 `kind` 設成 `page`，程式會抽取頁面上的連結，再用標題做初步分類。

## 下一步可以加的功能

- 加入更多來源，例如學術論文、專利、咖啡設備品牌公告、產區組織新聞
- 依「農場」「處理法」「氣候科技」「設備」分成不同報告
- 把週報再同步到 Email、Telegram 或 Slack
