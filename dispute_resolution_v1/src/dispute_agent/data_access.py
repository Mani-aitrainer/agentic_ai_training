"""Data access layer.

All mock data lives as JSON under data/. This module is the single place that
knows how to read it. Nodes never touch the filesystem directly -- they go
through a JsonRepository. That indirection is what lets tests inject an
in-memory repository and run the whole graph offline.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import settings


class RecordNotFound(KeyError):
    """Raised when a requested id is not present in the mock data."""


class JsonRepository:
    """Loads and serves the mock banking records.

    Files are read once and cached in memory. Each getter raises
    RecordNotFound on a missing id so callers can handle it explicitly
    rather than getting a bare KeyError from deep in the stack.
    """

    def __init__(self, data_dir: Path | None = None) -> None:
        self._data_dir = data_dir or settings.data_dir
        self._cache: dict[str, dict[str, Any]] = {}

    # -- low level ------------------------------------------------------
    def _load(self, name: str) -> dict[str, Any]:
        if name not in self._cache:
            path = self._data_dir / f"{name}.json"
            if not path.exists():
                raise FileNotFoundError(f"Mock data file missing: {path}")
            with path.open(encoding="utf-8") as fh:
                self._cache[name] = json.load(fh)
        return self._cache[name]

    def _get(self, collection: str, key: str) -> dict[str, Any]:
        table = self._load(collection)
        if key not in table:
            raise RecordNotFound(f"{key} not found in {collection}")
        return table[key]

    # -- public getters -------------------------------------------------
    def get_dispute(self, dispute_id: str) -> dict[str, Any]:
        return self._get("disputes", dispute_id)

    def get_transaction(self, txn_id: str) -> dict[str, Any]:
        return self._get("transactions", txn_id)

    def get_customer(self, customer_id: str) -> dict[str, Any]:
        return self._get("customers", customer_id)

    def get_merchant(self, merchant_id: str) -> dict[str, Any]:
        return self._get("merchants", merchant_id)

    def list_dispute_ids(self) -> list[str]:
        return list(self._load("disputes").keys())


class InMemoryRepository(JsonRepository):
    """A repository backed by dicts instead of files -- for fast unit tests."""

    def __init__(self, **tables: dict[str, Any]) -> None:  # noqa: D401
        super().__init__(data_dir=None)
        # pre-seed the cache so _load never hits disk
        self._cache = tables
