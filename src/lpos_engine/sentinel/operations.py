"""SO-026 record-only handlers for continuous Sentinel assurance."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ..engine import LPOSRuntime, RuntimeConfig
from ..store import SQLiteStore
from .models import SENTINEL_POLICY_VERSION


def _db_path(context: Mapping[str, Any]) -> Path:
    value = (
        context.get("database_path")
        or context.get("db_path")
        or os.environ.get("LPOS_STATE_DB")
        or (Path.home() / ".hermes" / "state" / "lpos.db")
    )
    return Path(value).expanduser().resolve()


def inventory_unassessed_artifacts(context: Mapping[str, Any]) -> Mapping[str, Any]:
    store = SQLiteStore(_db_path(context))
    pending = store.list_artifacts_without_sentinel_assessment(
        policy_version=SENTINEL_POLICY_VERSION
    )
    return {
        "policy_version": SENTINEL_POLICY_VERSION,
        "count": len(pending),
        "artifacts": [
            {
                "task_id": item.task_id,
                "artifact_id": item.artifact_id,
                "artifact_hash": item.content_hash,
            }
            for item in pending
        ],
        "mode": "passive_read_only",
    }


def assess_and_adversarially_review_artifacts(context: Mapping[str, Any]) -> Mapping[str, Any]:
    spec_root = context.get("spec_root")
    runtime = LPOSRuntime.local(
        RuntimeConfig(
            database_path=_db_path(context),
            spec_root=Path(spec_root) if spec_root else None,
            sentinel_enabled=True,
            sentinel_require_trusted_review=True,
        )
    )
    results = runtime.sentinel.run_pending()
    return {
        "processed": len(results),
        "trusted": sum(bool(item["trusted"]) for item in results),
        "rejected": sum(not bool(item["trusted"]) for item in results),
        "results": list(results),
        "external_side_effects": False,
    }


def report_sentinel_assurance_status(context: Mapping[str, Any]) -> Mapping[str, Any]:
    store = SQLiteStore(_db_path(context))
    pending = store.list_sentinel_reports(unacknowledged_only=True)
    status = store.sentinel_status()
    return {
        **status,
        "destination": "principal_security_inbox",
        "unacknowledged_reports": [
            {
                "report_id": item["report"].report_id,
                "task_id": item["report"].task_id,
                "artifact_hash": item["report"].artifact_hash,
                "overall": item["report"].overall,
                "summary": item["report"].summary,
            }
            for item in pending
        ],
        "raw_guild_findings_exposed": False,
    }


HANDLERS = {
    "inventory_unassessed_artifacts": inventory_unassessed_artifacts,
    "assess_and_adversarially_review_artifacts": assess_and_adversarially_review_artifacts,
    "report_sentinel_assurance_status": report_sentinel_assurance_status,
}
