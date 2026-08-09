"""Unit tests for the JSON data access layer."""
from __future__ import annotations

import pytest

from dispute_agent.data_access import (
    InMemoryRepository,
    JsonRepository,
    RecordNotFound,
)


def test_inmemory_repo_returns_seeded_record(repo):
    txn = repo.get_transaction("T_DUP")
    assert txn["amount"] == 8000.0
    assert txn["duplicate_of"] == "T_ORIG"


def test_missing_record_raises(repo):
    with pytest.raises(RecordNotFound):
        repo.get_transaction("DOES_NOT_EXIST")


def test_list_dispute_ids(repo):
    ids = repo.list_dispute_ids()
    assert set(ids) == {"D_DUP", "D_FRAUD", "D_SNR"}


def test_real_repo_reads_bundled_json():
    """The shipped data/ files load and the known ids are present."""
    repo = JsonRepository()
    dispute = repo.get_dispute("DSP001")
    assert dispute["txn_id"] == "TXN1002"
    txn = repo.get_transaction("TXN1002")
    assert txn["duplicate_of"] == "TXN1001"


def test_missing_file_raises(tmp_path):
    repo = JsonRepository(data_dir=tmp_path)
    with pytest.raises(FileNotFoundError):
        repo.get_dispute("anything")
