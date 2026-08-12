from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Article:
    title: str
    url: str
    published: datetime | None = None
    listed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ParsedPage:
    articles: tuple[Article, ...]
    next_url: str | None = None
