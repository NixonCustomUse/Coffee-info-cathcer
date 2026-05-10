"""Central configuration for Coffee Radar — edit API keys, URLs, and models here."""

from __future__ import annotations

import os


# ── LLM (OpenRouter) ──────────────────────────────────────────────
LLM_API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
LLM_API_URL = os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions")
LLM_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o")
LLM_TIMEOUT = 45


# ── Notion ────────────────────────────────────────────────────────
NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
NOTION_ARTICLES_DATABASE_ID = os.getenv("NOTION_ARTICLES_DATABASE_ID", "")
NOTION_SOURCES_DATABASE_ID = os.getenv("NOTION_SOURCES_DATABASE_ID", "")
NOTION_WEEKLY_PARENT_PAGE_ID = os.getenv("NOTION_WEEKLY_PARENT_PAGE_ID", "")
NOTION_VERSION = "2022-06-28"
