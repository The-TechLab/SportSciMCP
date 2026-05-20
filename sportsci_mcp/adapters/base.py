from __future__ import annotations

from abc import ABC, abstractmethod

from sportsci_mcp.models import SearchRecord


class LiteratureAdapter(ABC):
    name: str
    phase: int = 1
    requires_auth: bool = False

    @abstractmethod
    def search(
        self,
        query: str,
        *,
        max_results: int = 10,
        year_from: int | None = None,
        year_to: int | None = None,
    ) -> list[SearchRecord]:
        ...

    @abstractmethod
    def get(self, record_id: str) -> SearchRecord:
        ...

    def is_enabled(self, cfg: dict) -> bool:
        return bool(cfg.get("enabled", False))


class DatasetAdapter(ABC):
    name: str
    phase: int = 2
    requires_auth: bool = False

    @abstractmethod
    def search(
        self,
        query: str,
        *,
        max_results: int = 10,
    ) -> list[SearchRecord]:
        ...

    @abstractmethod
    def get(self, record_id: str) -> SearchRecord:
        ...
