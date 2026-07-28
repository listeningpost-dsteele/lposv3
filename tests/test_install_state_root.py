from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SPEC = importlib.util.spec_from_file_location("lpos_release_installer", Path(__file__).parents[1] / "install.py")
assert SPEC and SPEC.loader
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


def test_default_state_root_honors_explicit_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    state = tmp_path / "state"
    monkeypatch.setenv("LPOS_STATE_ROOT", str(state))
    assert installer.default_state_root() == state


def test_state_root_must_be_outside_release(tmp_path: Path) -> None:
    release = tmp_path / "release"
    release.mkdir()
    with pytest.raises(ValueError, match="outside the immutable release tree"):
        installer.resolve_state_root(release / "state", release)


def test_external_state_root_is_accepted(tmp_path: Path) -> None:
    release = tmp_path / "release"
    state = tmp_path / "state"
    release.mkdir()
    assert installer.resolve_state_root(state, release) == state.resolve()
