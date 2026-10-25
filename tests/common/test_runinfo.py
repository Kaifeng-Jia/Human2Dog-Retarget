"""Provenance rules: runs record their code/external commits and refuse unpinned externals."""

import pytest

from h2d.common.runinfo import ProvenanceError, start_run


def test_provenance_records_commit_and_externals(monkeypatch):
    prov = start_run("T000_test", allow_dirty=True, allow_external_mismatch=True)
    assert prov["run_id"] == "T000_test"
    assert set(prov["git"]) >= {"commit", "branch", "describe", "dirty"}
    assert "xmorph" in prov["externals"]
    assert set(prov["configs"]) == {"b2z1.yaml", "external.yaml"}


def test_refuses_unpinned_external(monkeypatch, tmp_path):
    monkeypatch.setenv("XMORPH_ROOT", str(tmp_path))  # exists, but is not the pinned checkout
    with pytest.raises(ProvenanceError):
        start_run("T001_test", allow_dirty=True)


def test_refuses_missing_external(monkeypatch, tmp_path):
    monkeypatch.setenv("XMORPH_ROOT", str(tmp_path / "does_not_exist"))
    with pytest.raises(ProvenanceError):
        start_run("T002_test", allow_dirty=True, allow_external_mismatch=True)
