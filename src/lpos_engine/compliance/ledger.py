"""Tamper-evident evidence ledger for the compliance history (LPOS-08).

``history.jsonl`` is a hash-chained, append-only JSONL ledger:

- Every line carries ``seq`` (monotonic, starting at 1) and
  ``chain = sha256(prev_line_chain + canonical_json(entry_without_chain))``.
  The first line chains from the literal string ``"GENESIS"``.
- :func:`append_entries` is a true O(1) append: it reads only the tail of the
  file (never the whole file), opens the ledger with ``"a"``, writes one JSON
  line per entry, and fsyncs. It never rewrites existing bytes.
- Trimming is never silent. :func:`compact` archives the trimmed prefix to
  ``history-archive-<n>.jsonl`` verbatim and replaces it with a checkpoint
  line ``{"kind": "checkpoint", "covers_through_seq": N, "rollup_hash": ...}``
  whose ``chain`` carries the rolled-up chain state forward, so the retained
  suffix verifies unchanged.
- :func:`verify_history` walks the chain and detects edit, deletion,
  insertion, reorder, and (via the ``history.head.json`` sidecar) truncation.

Honest boundary
---------------
Hash-chaining makes tampering *detectable*; it does not *prevent* the account
that owns the files from regenerating the entire chain (including the head
sidecar). Non-repudiation requires evidence held outside that account. Two
hooks exist for that:

- If ``<hermes>/compliance/checkpoint-key`` exists (an admin-provisioned file
  the runtime account should not be able to read in a separated deployment),
  every checkpoint line written by :func:`compact` additionally carries an
  HMAC-SHA256 tag over the checkpoint body computed with that key. A
  regenerated chain that lacks the key cannot produce a valid tag, and
  :func:`verify_history` fails the checkpoint.
- Checkpoint lines (``covers_through_seq``, ``rollup_hash``) are small,
  self-contained commitments suitable for periodic export to an external
  append-only store; comparing exported checkpoints against the local ledger
  detects wholesale regeneration.
"""

from __future__ import annotations

import hashlib
import hmac as hmac_module
import json
import os
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

GENESIS = "GENESIS"
CHECKPOINT_KIND = "checkpoint"
HEAD_BASENAME = "history.head.json"
CHECKPOINT_KEY_BASENAME = "checkpoint-key"
_ARCHIVE_RE = re.compile(r"^history-archive-(\d+)\.jsonl$")
_TAIL_CHUNK = 8192


def canonical_json(value: Any) -> str:
    """Deterministic JSON encoding used for all chain and HMAC computation."""

    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def chain_hash(prev_chain: str, entry_without_chain: Mapping[str, Any]) -> str:
    payload = (str(prev_chain) + canonical_json(dict(entry_without_chain))).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def head_path(history_file: Path) -> Path:
    return history_file.parent / HEAD_BASENAME


def checkpoint_key_path(history_file: Path) -> Path:
    return history_file.parent / CHECKPOINT_KEY_BASENAME


def _read_checkpoint_key(history_file: Path) -> bytes | None:
    try:
        raw = checkpoint_key_path(history_file).read_bytes().strip()
    except OSError:
        return None
    return raw or None


def _hmac_tag(key: bytes, body_without_hmac: Mapping[str, Any]) -> str:
    return hmac_module.new(
        key, canonical_json(dict(body_without_hmac)).encode("utf-8"), hashlib.sha256
    ).hexdigest()


def _tail_entry(history_file: Path) -> dict[str, Any] | None:
    """Read the last non-empty line of the ledger without loading the file."""

    try:
        size = history_file.stat().st_size
    except OSError:
        return None
    if size == 0:
        return None
    buffer = b""
    with open(history_file, "rb") as fh:
        position = size
        while position > 0:
            step = min(_TAIL_CHUNK, position)
            position -= step
            fh.seek(position)
            buffer = fh.read(step) + buffer
            stripped = buffer.rstrip(b"\n")
            if b"\n" in stripped:
                last = stripped.rsplit(b"\n", 1)[-1]
                break
        else:
            last = buffer.rstrip(b"\n")
    last = last.strip()
    if not last:
        return None
    try:
        value = json.loads(last.decode("utf-8", errors="replace"))
    except ValueError:
        return None
    return dict(value) if isinstance(value, Mapping) else None


def _write_head(history_file: Path, last_seq: int, last_chain: str) -> None:
    path = head_path(history_file)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps({"last_seq": last_seq, "last_chain": last_chain}) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, path)


def _read_head(history_file: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(head_path(history_file).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return dict(value) if isinstance(value, Mapping) else None


def append_entries(
    history_file: Path, entries: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    """True append: ``open("a")``, one chained JSON line per entry, fsync.

    Never reads more than the tail of the existing file, never rewrites any
    existing byte. Returns the appended entries with ``seq`` and ``chain`` set.
    """

    history_file = Path(history_file)
    from ..store import secure_create_file, secure_mkdir

    secure_mkdir(history_file.parent)
    last = _tail_entry(history_file)
    seq = int(last.get("seq", 0)) if last else 0
    prev_chain = str(last.get("chain", GENESIS)) if last else GENESIS

    appended: list[dict[str, Any]] = []
    if not entries:
        return appended
    secure_create_file(history_file)  # LPOS-15: 0600 on first create
    with open(history_file, "a", encoding="utf-8") as fh:
        for entry in entries:
            body = {key: value for key, value in dict(entry).items() if key != "chain"}
            seq += 1
            body["seq"] = seq
            body["chain"] = chain_hash(prev_chain, body)
            fh.write(canonical_json(body) + "\n")
            prev_chain = body["chain"]
            appended.append(body)
        fh.flush()
        os.fsync(fh.fileno())
    _write_head(history_file, seq, prev_chain)
    return appended


def _raw_lines(history_file: Path) -> list[str]:
    try:
        text = history_file.read_text(encoding="utf-8")
    except OSError:
        return []
    return [line for line in text.splitlines() if line.strip()]


def _next_archive_path(history_file: Path) -> Path:
    highest = 0
    for path in history_file.parent.glob("history-archive-*.jsonl"):
        match = _ARCHIVE_RE.match(path.name)
        if match:
            highest = max(highest, int(match.group(1)))
    return history_file.parent / f"history-archive-{highest + 1}.jsonl"


def compact(history_file: Path, *, keep_last: int, now_iso: str) -> dict[str, Any]:
    """Explicit compaction: archive the prefix, replace it with a checkpoint.

    The trimmed prefix is copied verbatim to ``history-archive-<n>.jsonl``
    (never silently dropped). The new ledger begins with a checkpoint line
    whose ``chain`` equals the ``rollup_hash`` (the chain value of the last
    archived line), so the retained suffix verifies byte-for-byte unchanged.
    If ``<compliance>/checkpoint-key`` exists, the checkpoint also carries an
    HMAC-SHA256 tag with that key.
    """

    history_file = Path(history_file)
    lines = _raw_lines(history_file)
    if len(lines) <= keep_last:
        return {"compacted": False, "lines": len(lines), "keep_last": keep_last}

    prefix, suffix = lines[:-keep_last], lines[-keep_last:]
    try:
        last_archived = json.loads(prefix[-1])
    except ValueError as exc:
        raise ValueError(f"cannot compact: last archived line is not JSON: {exc}") from exc
    covers_through_seq = int(last_archived.get("seq", 0))
    rollup_hash = str(last_archived.get("chain", GENESIS))

    archive = _next_archive_path(history_file)
    tmp_archive = archive.with_suffix(archive.suffix + ".tmp")
    tmp_archive.write_text("".join(line + "\n" for line in prefix), encoding="utf-8")
    os.replace(tmp_archive, archive)

    checkpoint: dict[str, Any] = {
        "kind": CHECKPOINT_KIND,
        "event": CHECKPOINT_KIND,
        "ts": now_iso,
        "covers_through_seq": covers_through_seq,
        "rollup_hash": rollup_hash,
        "archive": archive.name,
        "archived_lines": len(prefix),
        "chain": rollup_hash,
    }
    key = _read_checkpoint_key(history_file)
    if key is not None:
        body_without_hmac = {k: v for k, v in checkpoint.items() if k != "hmac"}
        checkpoint["hmac"] = _hmac_tag(key, body_without_hmac)

    tmp = history_file.with_suffix(history_file.suffix + ".tmp")
    tmp.write_text(
        canonical_json(checkpoint) + "\n" + "".join(line + "\n" for line in suffix),
        encoding="utf-8",
    )
    os.replace(tmp, history_file)
    return {
        "compacted": True,
        "archive": str(archive),
        "archived_lines": len(prefix),
        "covers_through_seq": covers_through_seq,
        "rollup_hash": rollup_hash,
        "hmac_signed": key is not None,
        "lines": len(suffix) + 1,
    }


def verify_history_file(history_file: Path) -> dict[str, Any]:
    """Walk the chain; detect edit, deletion, insertion, reorder, truncation.

    Returns ``{"ok", "first_bad_seq", "lines", "gaps", "reason"}``.
    ``first_bad_seq`` is the sequence number at which verification first
    failed (None when ok); ``gaps`` lists ``[expected_seq, found]`` pairs.
    """

    history_file = Path(history_file)
    lines = _raw_lines(history_file)
    key = _read_checkpoint_key(history_file)
    prev_chain = GENESIS
    expected_seq = 1
    gaps: list[list[Any]] = []
    ok = True
    first_bad_seq: int | None = None
    reason = ""

    for index, line in enumerate(lines):
        try:
            entry = json.loads(line)
        except ValueError:
            ok, first_bad_seq, reason = False, expected_seq, "malformed line"
            break
        if not isinstance(entry, Mapping):
            ok, first_bad_seq, reason = False, expected_seq, "non-object line"
            break
        entry = dict(entry)

        if entry.get("kind") == CHECKPOINT_KIND:
            if index != 0:
                ok, first_bad_seq = False, expected_seq
                reason = "checkpoint line not at the head of the ledger"
                break
            rollup = str(entry.get("rollup_hash", ""))
            if entry.get("chain") != rollup or not rollup:
                ok, first_bad_seq = False, expected_seq
                reason = "checkpoint chain does not carry its rollup_hash"
                break
            if key is not None:
                body_without_hmac = {k: v for k, v in entry.items() if k != "hmac"}
                tag = entry.get("hmac")
                if not tag or not hmac_module.compare_digest(
                    str(tag), _hmac_tag(key, body_without_hmac)
                ):
                    ok = False
                    first_bad_seq = int(entry.get("covers_through_seq", 0)) or expected_seq
                    reason = "checkpoint HMAC missing or invalid for the provisioned key"
                    break
            prev_chain = rollup
            expected_seq = int(entry.get("covers_through_seq", 0)) + 1
            continue

        seq = entry.get("seq")
        if seq != expected_seq:
            ok, first_bad_seq = False, expected_seq
            gaps.append([expected_seq, seq])
            reason = "sequence break (deleted, inserted, or reordered line)"
            break
        body = {k: v for k, v in entry.items() if k != "chain"}
        if entry.get("chain") != chain_hash(prev_chain, body):
            ok, first_bad_seq = False, int(seq)
            reason = "chain hash mismatch (edited or reordered line)"
            break
        prev_chain = str(entry["chain"])
        expected_seq = int(seq) + 1

    if ok:
        head = _read_head(history_file)
        if head is not None:
            head_seq = int(head.get("last_seq", 0))
            last_seq = expected_seq - 1
            if last_seq < head_seq:
                ok, first_bad_seq = False, last_seq + 1
                gaps.append([last_seq + 1, head_seq])
                reason = "truncation (head sidecar records a later sequence)"
            elif last_seq == head_seq and head_seq > 0 and prev_chain != str(
                head.get("last_chain", "")
            ):
                ok, first_bad_seq = False, head_seq
                reason = "tail chain does not match the head sidecar (rewritten ledger)"

    return {
        "ok": ok,
        "first_bad_seq": first_bad_seq,
        "lines": len(lines),
        "gaps": gaps,
        "reason": reason,
    }
