# Coffee Radar Enhancement Design

## Overview

三段式改進：B (資料層) → D (網頁儀表板) → A (Telegram 強化)。每段獨立可交付。

## Phase B — Reddit 社群來源

### 新 parser: `parse_reddit()`

新增 `reddit` kind 專用 parser，與現有 `parse_feed` 分離。

**位置：** `coffee/parsers.py`

**輸入：** Reddit RSS (Atom) feed XML + `Source` object

**輸出：** `list[Item]`

**邏輯：**

1. 用 `xml.etree.ElementTree` 解析 Atom feed
2. 從 `<entry>` 提取：
   - `title` → `item.title`
   - `link` (alternate) → `item.url`
   - `published` → `item.published`
   - `content` 或 `summary` → `item.summary` (抓 selftext 或外部連結描述)
3. 從每個 `<entry>` 的 `media:rating` 或 `media:description` 檢查 `over_18`（但 Reddit RSS 不直接提供此欄位，跳過）
4. 從 title / summary 提取打賞指標暗示（暫不實作 upvote 解析，RSS 不包含）

### Scoring 加成

- RSS feed 不包含 upvote/comment 數據，故無法定義基於社群互動的 score 加成。
- 改用分類關鍵詞匹配（同既有 `classify()` 機制，不需額外邏輯）。

### 新來源 (sources.json)

```json
{ "name": "r/coffee",       "url": "https://www.reddit.com/r/coffee/.rss",       "kind": "reddit", "enabled": true },
{ "name": "r/espresso",     "url": "https://www.reddit.com/r/espresso/.rss",     "kind": "reddit", "enabled": true },
{ "name": "r/roasting",     "url": "https://www.reddit.com/r/roasting/.rss",     "kind": "reddit", "enabled": true },
{ "name": "r/pourover",     "url": "https://www.reddit.com/r/pourover/.rss",     "kind": "reddit", "enabled": true },
{ "name": "r/cafe",         "url": "https://www.reddit.com/r/cafe/.rss",         "kind": "reddit", "enabled": true },
{ "name": "r/coffeesnobs",  "url": "https://www.reddit.com/r/coffeesnobs/.rss",  "kind": "reddit", "enabled": true },
```

### 整合到 collector

`coffee_radar.py` 中的 `collect()` 需增加 `"reddit"` → `parse_reddit` 的對應。

### 測試

- `tests/test_coffee_radar.py` 新增 `test_reddit_parser()`，用樣本 Reddit RSS XML 驗證。
- 確認 Reddit 的 title/summary 正確分類。

---

## Phase D — 互動式 HTML 儀表板

### 目標

取代現有 `generate_html.py` 的靜態列表，改為**單頁 HTML + 內嵌 JS**，無任何外部依賴。

### 功能

- **分類過濾**：多選 dropdown（從資料自動提取分類列表）
- **來源過濾**：多選 dropdown
- **日期範圍**：起始日 + 結束日 input
- **排序**：分數高→低 / 日期新→舊
- **搜尋**：關鍵字即時過濾 title + summary
- **卡片列表**：每個 item 一張卡，顯示分數、標題、來源、分類標籤、摘要、matched terms

### 技術方案

- Single HTML file, CSS in `<style>`, JS in `<script>`
- 資料以 JSON 內嵌於 `<script id="data">`
- 過濾邏輯：全部在前端即時處理，無後端
- 無 dependencies（純 vanilla JS）

### 產生方式

沿用 `generate_html.py` CLI，但輸出改為上述互動式報表。

---

## Phase A — Telegram 強化

*(待 B + D 完成後再細部設計)*

初步方向：
- 圖片預覽（若 item 有 og:image）
- 內聯按鈕（來源連結、分類快速查詢）
- 週末精選摘要
- 更精簡的排版

---

## 非功能性要求

- 零外部依賴（純 Python stdlib + vanilla JS）
- 繁體中文輸出
- 向後相容：現有 `data/items.jsonl` / `data/items.enriched.jsonl` 格式不變
