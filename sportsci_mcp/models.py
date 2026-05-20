from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


RecordType = Literal["paper", "dataset", "webpage", "unknown"]


@dataclass
class SearchRecord:
    source: str
    id: str
    type: RecordType
    title: str
    url: str
    abstract: str = ""
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    journal: str = ""
    doi: str = ""
    license: str = ""
    tags: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def ref(self) -> str:
        return f"{self.source}:{self.id}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
