"""Evidence-ledger integrity tests (audit finding LPOS-08) and verdict math.

Covers the tamper-evident hash chain: the audit's exact row-removal
reproduction must now be detected, along with edit, truncation, reorder, and
full-chain regeneration (via the HMAC'd checkpoint). Also covers the
threshold boundary math behind the LPOS-01 verdict tiers.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from lpos_engine.compliance import (
    Control,
    ControlResult,
    compact_history,
    run_audit,
    verify_history,
)
from lpos_engine.compliance import audit as audit_module
from lpos_engine.compliance import ledger

REPO_ROOT = Path(__file__).resolve().parents[1]


def _entries(count: int, *, control_id: str = "CTRL-X", start_minute: int = 0) -> list[dict]:
    base = datetime(2026, 7, 1, tzinfo=timezone.utc)
    return [
        {
            "ts": (base + timedelta(minutes=start_minute + i)).isoformat(),
            "run_id": f"RUN-{start_minute + i:05d}",
            "event": "check",
            "control_id": control_id,
            "passing": True,
            "evidence": f"seed {start_minute + i}",
        }
        for i in range(count)
    ]


def _history_file(hermes: Path) -> Path:
    return hermes / "compliance" / "history.jsonl"


def _passing_control(control_id: str = "CTRL-TEST-OUT", assurance: str = "outcome") -> Control:
    return Control(
        control_id=control_id,
        tsc_id="CC5",
        title="Always-passing test control",
        description="Always passes.",
        category="standard",
        check=lambda repo, hermes: ControlResult(passing=True, evidence="ok"),
        assurance=assurance,
    )


def _seed_runs(hermes: Path, control_id: str, *, runs: int, days: int) -> None:
    base = datetime.now(timezone.utc).replace(microsecond=0)
    entries = []
    for i in range(runs):
        day = (i % days) + 1  # past days only; run_audit adds today itself
        stamp = base - timedelta(days=day, minutes=i)
        entries.append(
            {
                "ts": stamp.isoformat(),
                "run_id": f"RUN-SEED-{i:04d}",
                "event": "check",
                "control_id": control_id,
                "passing": True,
                "evidence": "seed",
            }
        )
    audit_module.append_history(hermes, entries)


class AppendOnlyTests(unittest.TestCase):
    def test_append_never_rewrites_prior_bytes_and_strictly_grows(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            hermes = Path(directory)
            audit_module.append_history(hermes, _entries(5))
            path = _history_file(hermes)
            before_bytes = path.read_bytes()
            before_size = len(before_bytes)
            self.assertGreater(before_size, 0)

            audit_module.append_history(hermes, _entries(3, start_minute=5))
            after_bytes = path.read_bytes()
            self.assertGreater(len(after_bytes), before_size, "file size must strictly grow")
            self.assertEqual(
                after_bytes[:before_size], before_bytes,
                "prior bytes must be byte-identical after append",
            )

    def test_lines_carry_monotonic_seq_and_chain_from_genesis(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            hermes = Path(directory)
            audit_module.append_history(hermes, _entries(4))
            lines = [json.loads(l) for l in _history_file(hermes).read_text().splitlines()]
            self.assertEqual([e["seq"] for e in lines], [1, 2, 3, 4])
            prev = "GENESIS"
            for entry in lines:
                body = {k: v for k, v in entry.items() if k != "chain"}
                expected = hashlib.sha256(
                    (prev + ledger.canonical_json(body)).encode("utf-8")
                ).hexdigest()
                self.assertEqual(entry["chain"], expected)
                prev = entry["chain"]

    def test_fresh_ledger_verifies_ok(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            hermes = Path(directory)
            audit_module.append_history(hermes, _entries(10))
            result = verify_history(hermes)
            self.assertTrue(result["ok"])
            self.assertIsNone(result["first_bad_seq"])
            self.assertEqual(result["lines"], 10)
            self.assertEqual(result["gaps"], [])


class TamperDetectionTests(unittest.TestCase):
    def _write_lines(self, hermes: Path, lines: list[str]) -> None:
        _history_file(hermes).write_text("".join(line + "\n" for line in lines))

    def test_audit_reproduction_removing_a_history_row_is_detected(self) -> None:
        """The audit's exact tamper: remove one control's row -> verify fails."""

        with tempfile.TemporaryDirectory() as directory:
            hermes = Path(directory)
            run_audit(REPO_ROOT, hermes)  # real catalog, one execution
            path = _history_file(hermes)
            lines = path.read_text().splitlines()
            removed = [json.loads(l) for l in lines if json.loads(l)["control_id"] == "CTRL-CC1-01"]
            self.assertEqual(len(removed), 1)
            removed_seq = removed[0]["seq"]
            self._write_lines(
                hermes, [l for l in lines if json.loads(l)["control_id"] != "CTRL-CC1-01"]
            )
            result = verify_history(hermes)
            self.assertFalse(result["ok"])
            self.assertEqual(result["first_bad_seq"], removed_seq)

    def test_removing_a_middle_line_fails_at_that_seq(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            hermes = Path(directory)
            audit_module.append_history(hermes, _entries(9))
            lines = _history_file(hermes).read_text().splitlines()
            del lines[4]  # seq 5
            self._write_lines(hermes, lines)
            result = verify_history(hermes)
            self.assertFalse(result["ok"])
            self.assertEqual(result["first_bad_seq"], 5)
            self.assertIn([5, 6], result["gaps"])

    def test_editing_a_line_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            hermes = Path(directory)
            audit_module.append_history(hermes, _entries(6))
            lines = _history_file(hermes).read_text().splitlines()
            entry = json.loads(lines[2])
            entry["passing"] = False  # flip an outcome, keep the recorded chain
            lines[2] = json.dumps(entry, sort_keys=True)
            self._write_lines(hermes, lines)
            result = verify_history(hermes)
            self.assertFalse(result["ok"])
            self.assertEqual(result["first_bad_seq"], 3)

    def test_reordering_lines_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            hermes = Path(directory)
            audit_module.append_history(hermes, _entries(6))
            lines = _history_file(hermes).read_text().splitlines()
            lines[2], lines[3] = lines[3], lines[2]
            self._write_lines(hermes, lines)
            result = verify_history(hermes)
            self.assertFalse(result["ok"])
            self.assertEqual(result["first_bad_seq"], 3)

    def test_inserting_a_forged_line_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            hermes = Path(directory)
            audit_module.append_history(hermes, _entries(5))
            lines = _history_file(hermes).read_text().splitlines()
            forged = json.loads(lines[2])
            forged["evidence"] = "forged"
            lines.insert(3, json.dumps(forged, sort_keys=True))
            self._write_lines(hermes, lines)
            self.assertFalse(verify_history(hermes)["ok"])

    def test_truncation_is_detected_via_the_head_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            hermes = Path(directory)
            audit_module.append_history(hermes, _entries(8))
            lines = _history_file(hermes).read_text().splitlines()
            self._write_lines(hermes, lines[:5])  # drop the last 3 lines
            result = verify_history(hermes)
            self.assertFalse(result["ok"])
            self.assertEqual(result["first_bad_seq"], 6)
            self.assertIn([6, 8], result["gaps"])

    def test_whole_file_deletion_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            hermes = Path(directory)
            audit_module.append_history(hermes, _entries(4))
            _history_file(hermes).unlink()
            result = verify_history(hermes)
            self.assertFalse(result["ok"])


class CompactionTests(unittest.TestCase):
    def test_compaction_checkpoints_archives_and_still_verifies(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            hermes = Path(directory)
            audit_module.append_history(hermes, _entries(50))
            summary = compact_history(hermes, keep_last=20)
            self.assertTrue(summary["compacted"])
            self.assertEqual(summary["covers_through_seq"], 30)

            # The trimmed prefix is archived verbatim, never silently dropped.
            archive = Path(summary["archive"])
            self.assertTrue(archive.is_file())
            archived = [json.loads(l) for l in archive.read_text().splitlines()]
            self.assertEqual([e["seq"] for e in archived], list(range(1, 31)))

            # The active ledger: checkpoint line + retained suffix, verifiable.
            lines = [json.loads(l) for l in _history_file(hermes).read_text().splitlines()]
            self.assertEqual(lines[0]["kind"], "checkpoint")
            self.assertEqual(lines[0]["covers_through_seq"], 30)
            self.assertEqual(lines[0]["rollup_hash"], archived[-1]["chain"])
            self.assertEqual([e["seq"] for e in lines[1:]], list(range(31, 51)))
            self.assertTrue(verify_history(hermes)["ok"])

            # Appends continue the chain across the checkpoint.
            audit_module.append_history(hermes, _entries(3, start_minute=50))
            self.assertTrue(verify_history(hermes)["ok"])

    def test_no_compaction_below_the_limit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            hermes = Path(directory)
            audit_module.append_history(hermes, _entries(5))
            summary = compact_history(hermes, keep_last=20)
            self.assertFalse(summary["compacted"])
            self.assertEqual(len(_history_file(hermes).read_text().splitlines()), 5)

    def test_tampering_after_compaction_is_still_detected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            hermes = Path(directory)
            audit_module.append_history(hermes, _entries(40))
            compact_history(hermes, keep_last=10)
            lines = _history_file(hermes).read_text().splitlines()
            del lines[5]  # remove a retained line after the checkpoint
            _history_file(hermes).write_text("".join(l + "\n" for l in lines))
            self.assertFalse(verify_history(hermes)["ok"])


class HmacCheckpointTests(unittest.TestCase):
    def test_checkpoint_carries_hmac_when_key_exists_and_verifies(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            hermes = Path(directory)
            audit_module.append_history(hermes, _entries(30))
            key_file = hermes / "compliance" / "checkpoint-key"
            key_file.write_bytes(b"admin-held-secret-key")
            summary = compact_history(hermes, keep_last=10)
            self.assertTrue(summary["hmac_signed"])
            checkpoint = json.loads(_history_file(hermes).read_text().splitlines()[0])
            self.assertIn("hmac", checkpoint)
            self.assertTrue(verify_history(hermes)["ok"])

    def test_full_chain_regeneration_without_the_key_fails_verification(self) -> None:
        """LPOS-08 honest boundary: the account owner can rebuild the whole
        chain, but without the admin checkpoint key the regenerated checkpoint
        cannot carry a valid HMAC tag."""

        with tempfile.TemporaryDirectory() as directory:
            hermes = Path(directory)
            audit_module.append_history(hermes, _entries(30))
            key_file = hermes / "compliance" / "checkpoint-key"
            key_file.write_bytes(b"admin-held-secret-key")
            compact_history(hermes, keep_last=10)
            self.assertTrue(verify_history(hermes)["ok"])

            # Attacker: remove one retained entry and regenerate EVERYTHING —
            # seqs, chains, the checkpoint rollup, and the head sidecar — but
            # they do not hold the key, so the tag cannot be recomputed.
            path = _history_file(hermes)
            lines = [json.loads(l) for l in path.read_text().splitlines()]
            checkpoint, entries = lines[0], lines[1:]
            del entries[3]
            prev = checkpoint["rollup_hash"]
            seq = int(checkpoint["covers_through_seq"])
            rebuilt = []
            for entry in entries:
                body = {k: v for k, v in entry.items() if k != "chain"}
                seq += 1
                body["seq"] = seq
                body["chain"] = ledger.chain_hash(prev, body)
                prev = body["chain"]
                rebuilt.append(body)
            forged_checkpoint = {k: v for k, v in checkpoint.items() if k != "hmac"}
            forged_checkpoint["hmac"] = "0" * 64  # cannot compute without the key
            path.write_text(
                "".join(
                    ledger.canonical_json(e) + "\n"
                    for e in [forged_checkpoint, *rebuilt]
                )
            )
            ledger._write_head(path, seq, prev)  # attacker rewrites the sidecar too

            result = verify_history(hermes)
            self.assertFalse(result["ok"])
            self.assertIn("HMAC", result["reason"])


class VerdictBoundaryTests(unittest.TestCase):
    def test_29_distinct_days_is_insufficient_30_is_operating(self) -> None:
        for past_days, expected in ((28, "insufficient_history"), (29, "operating")):
            with tempfile.TemporaryDirectory() as directory:
                hermes = Path(directory)
                control = _passing_control()
                # past_days seeded distinct days + today's run = past_days + 1.
                _seed_runs(hermes, control.control_id, runs=past_days, days=past_days)
                result = run_audit(REPO_ROOT, hermes, controls=[control])
                doc = result.status["controls"][0]
                self.assertEqual(doc["distinct_run_days"], past_days + 1)
                self.assertGreaterEqual(doc["distinct_runs"], 20)
                self.assertEqual(doc["verdict"], expected, f"{past_days + 1} days")

    def test_19_distinct_runs_vs_20_boundary(self) -> None:
        # distinct run days can never exceed distinct runs, so with the
        # shipped constants the run threshold binds only alongside the day
        # threshold; the day requirement is relaxed here to isolate the
        # 19-vs-20 run boundary math.
        for seeded, expected in ((18, "insufficient_history"), (19, "operating")):
            with tempfile.TemporaryDirectory() as directory:
                hermes = Path(directory)
                control = _passing_control()
                _seed_runs(hermes, control.control_id, runs=seeded, days=min(seeded, 5))
                with mock.patch.object(audit_module, "MIN_OBSERVATION_DAYS", 1):
                    result = run_audit(REPO_ROOT, hermes, controls=[control])
                doc = result.status["controls"][0]
                self.assertEqual(doc["distinct_runs"], seeded + 1)
                self.assertEqual(doc["verdict"], expected, f"{seeded + 1} runs")

    def test_overall_thresholds_flip_insufficient_evidence_to_ready(self) -> None:
        for past_days, expected in (
            (28, "insufficient_evidence"),
            (29, "ready_pending_attestation"),
        ):
            with tempfile.TemporaryDirectory() as directory:
                hermes = Path(directory)
                control = _passing_control()
                _seed_runs(hermes, control.control_id, runs=past_days, days=past_days)
                result = run_audit(REPO_ROOT, hermes, controls=[control])
                self.assertEqual(result.overall, expected, f"{past_days + 1} days")

    def test_structural_control_is_capped_even_with_perfect_long_history(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            hermes = Path(directory)
            control = _passing_control("CTRL-TEST-STRUCT", assurance="structural")
            _seed_runs(hermes, control.control_id, runs=80, days=60)
            result = run_audit(REPO_ROOT, hermes, controls=[control])
            doc = result.status["controls"][0]
            self.assertEqual(doc["pass_ratio"], 1.0)
            self.assertEqual(doc["verdict"], "structural_evidence_only")
            self.assertNotEqual(doc["verdict"], "operating")


if __name__ == "__main__":
    unittest.main()
