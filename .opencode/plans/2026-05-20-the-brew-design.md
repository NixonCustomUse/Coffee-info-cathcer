# The Brew — Newspaper-style Dashboard Redesign

## Overview

Redesign the Coffee Info Catcher website as a newspaper-style dashboard called **The Brew**. Strip the two-phase landing/dashboard flow and replace with a single-page editorial layout reminiscent of *The Guardian* / *NYT* — cream paper background, serif typography, clean grid of article cards.

## Goals

- Design refresh: dark coffee-house → light newspaper aesthetic
- Single-page: no landing screen, content immediately visible
- Typography-forward: distinctive serif headlines, refined sans body
- Responsive: 2-column grid on desktop, 1-column on mobile
- Preserve all existing functionality: category/subcategory filtering, score badge, source/date metadata, click-to-open links

## Aesthetic Direction

| Element | Choice |
|---------|--------|
| Tone | Editorial / newspaper — refined, trustworthy, clean |
| Background | Off-white cream `#f6f3ee` (paper) |
| Text | Near-black `#1a1a1a`, warm gray `#8a8478` for muted |
| Accent | Deep burgundy `#8b1a1a` |
| Card BG | White `#ffffff` with thin `#e0ddd6` borders |
| Nameplate | Playfair Display (keep existing, works well) |
| Headline font | **Lora** — serif, readable, characterful |
| Body font | **Source Sans 3** — clean sans, not generic |
| Mono font | **JetBrains Mono** — keep existing, for score badges |
| Layout | Single page, max-width ~1200px centered |
| Card grid | 2 columns desktop, 1 column mobile |

## Structure

```
┌──────────────────────────────────────────────┐
│  THE BREW                                     │
│  Wednesday, 20 May 2026 · 110 signals        │
│  ─────────────────────────────────────────    │
│  [All] [Climate] [Market] [Roasting] [Farm]   │
│  [Equipment] [Processing]                     │
│  [subcategory chips: Automation, Espresso...] │
├──────────────────────────────────────────────┤
│                                              │
│  ┌──────────────┐  ┌──────────────┐          │
│  │ 14           │  │ 12           │          │
│  │ Headline     │  │ Another      │          │
│  │ Source·May20 │  │ Source·May20 │          │
│  │ [tag] [tag]  │  │ [tag] [tag]  │          │
│  │ Summary...   │  │ Summary...   │          │
│  └──────────────┘  └──────────────┘          │
│                                              │
│  ┌──────────────┐  ┌──────────────┐          │
│  │ ...          │  │ ...          │          │
│  └──────────────┘  └──────────────┘          │
└──────────────────────────────────────────────┘
```

## Components

### 1. Masthead
- Newspaper nameplate: **THE BREW** in Playfair Display, large, tracked out slightly
- Below: date (auto-generated) + signal count + source count
- Thin horizontal rule (`#e0ddd6`) separating header from content

### 2. Filter Bar
- Horizontal row of pill buttons for categories
- Active state: deep burgundy `#8b1a1a` filled, white text
- Inactive: transparent, thin `#d0ccc4` border
- All button always first, shows total count
- Subcategory chips below, same style but smaller

### 3. Stats Bar
- Compact row between filters and cards showing: "XX signals · XX sources"
- Muted warm gray typography, small

### 4. Article Cards
Each card contains:
- **Score badge** (top-left corner): small box, burgundy bg, JetBrains Mono, white text — styled like a newspaper folio / price stamp
- **Headline**: Lora serif, medium weight, ~1rem, leading-tight, one or two lines
- **Meta line**: Source name (burgundy accent) · date — small, warm gray
- **Category tags**: small pill badges, warm off-white bg, muted text
- **Subcategory tags**: smaller, lighter, subtle border
- **Summary**: 2-3 line clamped excerpt in Source Sans 3, warm gray
- **Hover**: subtle lift (`translateY(-2px)`) + thin burgundy top border appears
- **Click**: opens article URL in new tab

### 5. Empty State
Center-aligned message when no articles match filters: "No articles match your filters." in warm gray.

### 6. Reset Filters button
Appears only when a filter is active. Small text link: "← All articles" in burgundy.

## Data Handling
- Data stays **hardcoded inline** as a JS constant (same as current `DATA` array) for CF Workers simplicity
- Structure is already enriched JSONL with `t`, `s`, `u`, `p`, `c`, `sc`, `tc`, `su` fields — no change needed

## Mobile
- Cards stack to single column
- Filter bar scrolls horizontally
- Same typography, same off-white bg
- Fixed bottom bar with signal/source count + reset link
- Score badge stays in corner, slightly smaller

## What stays the same
- The `DATA` array format (same fields)
- JavaScript filtering logic (`setFilter`, `setSub`, `filtered()`, `getSources`, `getCategories`, `getSubcategories`)
- `esc()` utility
- `onclick="window.open(...)"` for article links

## What changes
- Remove landing section entirely
- Remove radar SVG/CSS
- Remove `loadDashboard()` / `resetView()` functions
- Remove separate mobile dashboard markup — single responsive layout
- Rewrite CSS: cream bg, newspaper typography, burgundy accent
- Replace fonts: add Lora, Source Sans 3 via Google Fonts
- Card HTML structure changes to newspaper-clipping style
- Score badge moves to prominent box in top-left

## Out of Scope
- Server-side rendering / dynamic data fetching
- Full-text search
- Date range filters
- Pagination
- Dark mode toggle
