from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from lpos_engine.coe_manifest import MANIFEST_NAME, generate_manifest, verify_release

IDENTITY = {
    "product": "chip-service",
    "release_version": "4.5.0",
    "release_channel": "stable",
    "lpos_version": "4.5.0",
}
COMMIT = "a" * 40


def make_release(root: Path) -> dict:
    (root / "package.json").write_text('{"version":"4.5.0"}\n', encoding="utf-8")
    (root / "assets").mkdir()
    (root / "assets" / "app.js").write_text("console.log('ok');\n", encoding="utf-8")
    return generate_manifest(root, release=IDENTITY, source_commit=COMMIT, build_id="build-1")


def manifest(root: Path) -> dict:
    return json.loads((root / MANIFEST_NAME).read_text(encoding="utf-8"))


def write_manifest(root: Path, value: dict) -> None:
    (root / MANIFEST_NAME).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_clean_release_passes(tmp_path: Path) -> None:
    created = make_release(tmp_path)
    result = verify_release(tmp_path, expected_identity=IDENTITY, expected_commit=COMMIT)
    assert result["status"] == "pass"
    assert result["file_count"] == 2
    assert result["artifact_sha256"] == created["artifact_sha256"]


@pytest.mark.parametrize("relative", ["package.json", "assets/app.js"])
def test_changed_file_fails(tmp_path: Path, relative: str) -> None:
    make_release(tmp_path)
    (tmp_path / relative).write_text("tampered", encoding="utf-8")
    with pytest.raises(ValueError, match="mismatch"):
        verify_release(tmp_path)


def test_missing_listed_file_fails(tmp_path: Path) -> None:
    make_release(tmp_path)
    (tmp_path / "assets" / "app.js").unlink()
    with pytest.raises(ValueError, match="missing release files"):
        verify_release(tmp_path)


def test_unlisted_file_fails(tmp_path: Path) -> None:
    make_release(tmp_path)
    (tmp_path / "extra.txt").write_text("extra", encoding="utf-8")
    with pytest.raises(ValueError, match="unlisted release files"):
        verify_release(tmp_path)


def test_mutable_status_file_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "app.js").write_text("ok", encoding="utf-8")
    (tmp_path / "status").mkdir()
    (tmp_path / "status" / "current.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="mutable or forbidden"):
        generate_manifest(tmp_path, release=IDENTITY, source_commit=COMMIT, build_id="build-1")


def test_manifest_tampering_fails(tmp_path: Path) -> None:
    make_release(tmp_path)
    value = manifest(tmp_path)
    value["artifact_sha256"] = "0" * 64
    write_manifest(tmp_path, value)
    with pytest.raises(ValueError, match="artifact identity"):
        verify_release(tmp_path)


def test_version_mismatch_fails(tmp_path: Path) -> None:
    make_release(tmp_path)
    wrong = dict(IDENTITY)
    wrong["release_version"] = "4.5.1"
    with pytest.raises(ValueError, match="release identity mismatch"):
        verify_release(tmp_path, expected_identity=wrong)


def test_commit_mismatch_fails(tmp_path: Path) -> None:
    make_release(tmp_path)
    with pytest.raises(ValueError, match="source commit mismatch"):
        verify_release(tmp_path, expected_commit="b" * 40)


def test_symlink_fails(tmp_path: Path) -> None:
    make_release(tmp_path)
    os.symlink("/etc/passwd", tmp_path / "escape")
    with pytest.raises(ValueError, match="symlink"):
        verify_release(tmp_path)


def test_path_traversal_fails(tmp_path: Path) -> None:
    make_release(tmp_path)
    value = manifest(tmp_path)
    value["files"][0]["path"] = "../escape"
    write_manifest(tmp_path, value)
    with pytest.raises(ValueError, match="unsafe release path"):
        verify_release(tmp_path)


def test_duplicate_path_fails(tmp_path: Path) -> None:
    make_release(tmp_path)
    value = manifest(tmp_path)
    value["files"].append(dict(value["files"][0]))
    write_manifest(tmp_path, value)
    with pytest.raises(ValueError, match="duplicate"):
        verify_release(tmp_path)


def test_permission_mismatch_fails(tmp_path: Path) -> None:
    make_release(tmp_path)
    target = tmp_path / "assets" / "app.js"
    target.chmod(0o755)
    with pytest.raises(ValueError, match="mode mismatch"):
        verify_release(tmp_path)


def test_corrupt_json_fails(tmp_path: Path) -> None:
    (tmp_path / MANIFEST_NAME).write_text("{", encoding="utf-8")
    with pytest.raises(ValueError, match="manifest is invalid"):
        verify_release(tmp_path)


def test_empty_manifest_fails(tmp_path: Path) -> None:
    value = {
        "schema_version": 1,
        "release": {"schema_version": 1, **IDENTITY},
        "source_commit": COMMIT,
        "build_id": "build-1",
        "generation_tool_version": "1",
        "created_at": "2026-07-28T00:00:00Z",
        "files": [],
        "artifact_sha256": "0" * 64,
    }
    write_manifest(tmp_path, value)
    with pytest.raises(ValueError, match="no file records"):
        verify_release(tmp_path)


def test_source_tree_with_mutable_content_is_not_a_release(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "HEAD").write_text("ref: refs/heads/main", encoding="utf-8")
    (tmp_path / "app.py").write_text("pass\n", encoding="utf-8")
    with pytest.raises(ValueError, match="forbidden"):
        generate_manifest(tmp_path, release=IDENTITY, source_commit=COMMIT, build_id="build-1")
