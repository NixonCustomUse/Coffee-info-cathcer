# Phase A: Telegram Enhancement

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add inline keyboard buttons to Telegram daily report + weekend digest mode.

**Architecture:** `send_telegram()` extended with `reply_markup` for inline buttons. New `--digest` flag on `coffee_telegram.py` generates weekend-style summary. `run_daily_sync.sh` calls digest mode on Sunday.

**Tech Stack:** Python stdlib only (`urllib.request` + `json`). Zero new dependencies.

---

### Task 1: Add inline keyboard support to Telegram sender

**Files:**
- Modify: `coffee_telegram.py`

- [ ] **Step 1: Read current coffee_telegram.py to understand structure**

- [ ] **Step 2: Add `build_keyboard()` function that generates inline keyboard markup**

```python
def build_keyboard(items: list[dict], max_buttons: int = 5) -> list[list[dict]]:
    keyboard = []
    for i, item in enumerate(items[:max_buttons]):
        url = item.get("url", "")
        title = item.get("title", "")
        if url:
            label = f"{i + 1}. {title[:40]}"
            keyboard.append([{"text": label, "url": url}])
    return keyboard
```

Add after `build_daily_body()`.

- [ ] **Step 3: Update `send_telegram()` to accept optional `reply_markup`**

Modify `send_telegram()` signature and payload:

```python
def send_telegram(
    text: str, token: str, chat_id: str,
    keyboard: list[list[dict]] | None = None,
) -> bool:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload: dict[str, object] = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if keyboard:
        payload["reply_markup"] = {"inline_keyboard": keyboard}

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status == 200
    except Exception as exc:
        print(f"Telegram send failed: {exc}", file=sys.stderr)
        return False
```

Key changes:
- New `keyboard` parameter
- `disable_web_page_preview` changed to `True` (buttons replace URLs, no need for previews)
- `ensure_ascii=False` in `json.dumps` to preserve Chinese characters

- [ ] **Step 4: Simplify `build_daily_body()` — remove inline links from text, keep shorter**

Replace `build_daily_body()`:

```python
def build_daily_body(items: list[dict], limit: int = 5) -> tuple[str, list[list[dict]]]:
    yesterday = dt.datetime.now(UTC).date() - dt.timedelta(days=1)

    filtered = []
    for i in items:
        pub = parse_date(i.get("published", ""))
        if pub and pub.date() == yesterday:
            filtered.append(i)

    if not filtered:
        return (
            f"☕ 咖啡日報 — {yesterday}\n"
            f"─────────────────\n"
            f"昨天沒有新訊號。",
            [],
        )

    top = sorted(filtered, key=lambda i: i.get("score", 0), reverse=True)[:limit]
    cats = Counter()
    for i in filtered:
        for c in i.get("categories", []):
            cats[c] += 1
    cat_summary = "、".join(f"{c}({n})" for c, n in cats.most_common())

    lines = [
        f"☕ 咖啡日報 — {yesterday}",
        f"─────────────────",
        f"昨天共 {len(filtered)} 則咖啡訊號",
        "",
        f"分類：{cat_summary}",
        "",
    ]

    for i, item in enumerate(top, 1):
        title = item.get("title", "")
        source = item.get("source", "")
        categories = "、".join(item.get("categories", []))
        summary = (item.get("zh_summary", "") or "").strip()
        lines.append(f"{i}. {title}")
        lines.append(f"   {source} · {categories}")
        if summary:
            short = summary[:100] + "…" if len(summary) > 100 else summary
            lines.append(f"   {short}")

    keyboard = build_keyboard(top)
    return "\n".join(lines), keyboard
```

Key changes:
- Returns `(str, keyboard)` tuple instead of just `str`
- Removed `<a href>` links from text (buttons handle navigation)
- Shorter summary (100 chars)
- Default limit changed from 10 to 5

- [ ] **Step 5: Update `main()` to pass keyboard to send_telegram**

```python
def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    items = load_jsonl(Path(args.input))
    text, keyboard = build_daily_body(items, limit=args.limit)

    if args.dry_run:
        print(text)
        if keyboard:
            print("\n--- keyboard ---")
            print(json.dumps(keyboard, ensure_ascii=False, indent=2))
        return 0

    token = args.token or os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = args.chat_id or os.getenv("TELEGRAM_CHAT_ID", "")

    if not token or not chat_id:
        print("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID", file=sys.stderr)
        return 1

    ok = send_telegram(text, token, chat_id, keyboard=keyboard)
    return 0 if ok else 1
```

- [ ] **Step 6: Run dry-run to verify format**

Run: `TELEGRAM_BOT_TOKEN=test TELEGRAM_CHAT_ID=test python3 coffee_telegram.py --dry-run`
Expected: formatted text + keyboard JSON printed (no yesterday data, so expect "昨天沒有新訊號")

- [ ] **Step 7: Run tests**

Run: `python3 -m unittest discover -s tests -v`
Expected: all 13 tests pass

- [ ] **Step 8: Commit**

```bash
git add coffee_telegram.py
git commit -m "feat: inline keyboard buttons + cleaner Telegram report"
```

---

### Task 2: Add weekend digest mode

**Files:**
- Modify: `coffee_telegram.py`
- Modify: `run_daily_sync.sh`

- [ ] **Step 1: Read current coffee_telegram.py**

- [ ] **Step 2: Add `build_digest_body()` function**

```python
def build_digest_body(items: list[dict], limit: int = 3) -> tuple[str, list[list[dict]]]:
    now = dt.datetime.now(UTC)
    monday = now - dt.timedelta(days=now.weekday())
    sunday = monday + dt.timedelta(days=6)

    filtered = []
    for i in items:
        pub = parse_date(i.get("published", ""))
        if pub and monday.date() <= pub.date() <= sunday.date():
            filtered.append(i)

    if not filtered:
        week_label = monday.strftime("%m/%d") + "~" + sunday.strftime("%m/%d")
        return (
            f"☕ 本週咖啡精選 — W{now.isocalendar()[1]}\n"
            f"─────────────────\n"
            f"{week_label} 沒有新訊號。",
            [],
        )

    # Group by date
    by_date: dict[dt.date, list[dict]] = {}
    for i in filtered:
        pub = parse_date(i.get("published", ""))
        if pub:
            by_date.setdefault(pub.date(), []).append(i)

    cats = Counter()
    for i in filtered:
        for c in i.get("categories", []):
            cats[c] += 1
    cat_summary = "、".join(f"{c}({n})" for c, n in cats.most_common())

    sources = len({i.get("source", "") for i in filtered})
    week_label = monday.strftime("%m/%d") + " ~ " + sunday.strftime("%m/%d")

    lines = [
        f"☕ 本週咖啡精選 — W{now.isocalendar()[1]}",
        f"─────────────────",
        f"{week_label} 共 {len(filtered)} 則 / {sources} 來源",
        "",
        f"分類：{cat_summary}",
        "",
    ]

    all_top_items: list[dict] = []
    for date in sorted(by_date.keys(), reverse=True):
        day_items = sorted(by_date[date], key=lambda i: i.get("score", 0), reverse=True)[:limit]
        date_label = date.strftime("%m/%d (%a)")
        lines.append(f"📅 {date_label}")
        for i, item in enumerate(day_items, 1):
            title = item.get("title", "")
            source = item.get("source", "")
            score = item.get("score", 0)
            categories = "、".join(item.get("categories", []))
            lines.append(f"  {i}. [{score}] {title}")
            lines.append(f"     {source} · {categories}")
        lines.append("")
        all_top_items.extend(day_items)

    keyboard = build_keyboard(all_top_items, max_buttons=10)
    return "\n".join(lines), keyboard
```

- [ ] **Step 3: Add `--digest` flag to argument parser**

```python
parser.add_argument("--digest", action="store_true", help="Generate weekly digest instead of daily report")
```

- [ ] **Step 4: Update `main()` to dispatch digest mode**

```python
def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    items = load_jsonl(Path(args.input))

    if args.digest:
        text, keyboard = build_digest_body(items)
    else:
        text, keyboard = build_daily_body(items, limit=args.limit)

    if args.dry_run:
        print(text)
        if keyboard:
            print("\n--- keyboard ---")
            print(json.dumps(keyboard, ensure_ascii=False, indent=2))
        return 0

    token = args.token or os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = args.chat_id or os.getenv("TELEGRAM_CHAT_ID", "")

    if not token or not chat_id:
        print("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID", file=sys.stderr)
        return 1

    ok = send_telegram(text, token, chat_id, keyboard=keyboard)
    return 0 if ok else 1
```

- [ ] **Step 5: Test digest dry-run**

Run: `python3 coffee_telegram.py --dry-run --digest`
Expected: digest-formatted text printed with weekly grouping

- [ ] **Step 6: Add digest call to run_daily_sync.sh for Sunday**

Edit `run_daily_sync.sh`, add after the daily telegram call:

```bash
# Sunday: send weekly digest
if [ "$(date +%u)" = "7" ]; then
  python3 coffee_telegram.py --input data/items.enriched.jsonl --digest
fi
```

- [ ] **Step 7: Run tests**

Run: `python3 -m unittest discover -s tests -v`
Expected: all 13 tests pass

- [ ] **Step 8: Commit**

```bash
git add coffee_telegram.py run_daily_sync.sh
git commit -m "feat: weekend digest mode with date-grouped items"
```

---

### Task 3: Final test + live verify

- [ ] **Step 1: Run full test suite**

Run: `python3 -m unittest discover -s tests -v`
Expected: 13/13 pass

- [ ] **Step 2: Send a live test message with current data**

Run:
```bash
cd /Users/nx/Documents/Coffee-info-cathcer
TELEGRAM_BOT_TOKEN="..." TELEGRAM_CHAT_ID="..." \
python3 coffee_telegram.py --dry-run --digest
```
Expected: properly formatted digest output. Then send it live:
```bash
TELEGRAM_BOT_TOKEN="..." TELEGRAM_CHAT_ID="..." python3 coffee_telegram.py --digest
```

- [ ] **Step 3: Commit any final tweaks**
