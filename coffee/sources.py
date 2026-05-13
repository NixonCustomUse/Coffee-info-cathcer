from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Source:
    name: str
    url: str
    kind: str = "feed"
    enabled: bool = True
    tags: list[str] = field(default_factory=list)


def load_sources(path: Path) -> list[Source]:
    raw_sources = json.loads(path.read_text(encoding="utf-8"))
    return [Source(**raw) for raw in raw_sources if raw.get("enabled", True)]
