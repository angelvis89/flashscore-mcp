from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True)
class MatchScore:
    home: str | None = None
    away: str | None = None


@dataclass(frozen=True)
class LiveMatch:
    match_id: str
    home: str
    away: str
    score: MatchScore = field(default_factory=MatchScore)
    status: str | None = None
    minute: str | None = None
    league: str | None = None
    country: str | None = None
    url: str | None = None
    scheduled_at: str | None = None
    favorite_available: bool = False
    betting_available: bool = False
    tv_available: bool = False
    raw_text: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LiveSnapshot:
    source: str
    fetched_at: str
    cache_ttl_seconds: int
    stale: bool
    items: list[LiveMatch]
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["items"] = [item.to_dict() for item in self.items]
        return data


@dataclass(frozen=True)
class MatchSection:
    name: str
    available: bool
    raw_text: str | None = None
    data: Any = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MatchDetail:
    match: LiveMatch
    fetched_at: str
    source: str
    sections: dict[str, MatchSection]
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "match": self.match.to_dict(),
            "fetched_at": self.fetched_at,
            "source": self.source,
            "sections": {key: section.to_dict() for key, section in self.sections.items()},
            "warnings": self.warnings,
        }
