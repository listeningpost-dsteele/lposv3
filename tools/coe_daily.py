#!/usr/bin/env python3
"""Run the deterministic 03:00 Central COE audit without waking a model."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any

from lpos_engine.coe_runtime import AuditOrchestrator, render_daily_report


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def _truth(name: str) -> bool:
    return os.environ.get(name, "").lower() == "true"


def _post_json(url: str, token: str, payload: dict[str, object]) -> dict[str, object]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers={"authorization": f"Bearer {token}", "content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    lpos_repo = Path(os.environ.get("COE_LPOS_REPO", "/Users/dan/lpos45-coe-v1")).resolve()
    app_repo = Path(os.environ.get("COE_APP_REPO", "/Users/dan/chip-service-coe-v1")).resolve()
    release_root = Path(os.environ["COE_RELEASE_ROOT"]).resolve()
    state_root = Path(os.environ.get("COE_STATE_DIR", str(Path.home() / ".hermes" / "state" / "chip-service"))).resolve()
    baseline_file = state_root / "coe" / "baselines.json"
    baselines: dict[str, str] = {}
    if baseline_file.is_file():
        baselines = json.loads(baseline_file.read_text(encoding="utf-8"))
    app_head = _git(app_repo, "rev-parse", "HEAD")
    lpos_head = _git(lpos_repo, "rev-parse", "HEAD")
    app_baseline = baselines.get(str(app_repo), os.environ.get("COE_APP_BASELINE_COMMIT", f"{app_head}^"))
    lpos_baseline = baselines.get(str(lpos_repo), os.environ.get("COE_LPOS_BASELINE_COMMIT", f"{lpos_head}^"))
    python = sys.executable
    test_state = str(state_root / "test-state")
    test_environment = {"CHIP_STATE_DIR": test_state, "COE_STATE_DIR": str(state_root / "test-coe-state")}
    configuration: dict[str, Any] = {
        key: os.environ.get(key)
        for key in (
            "COE_ENABLED", "COE_SCHEDULE_ENABLED", "COE_DASHBOARD_ENABLED", "COE_EMAIL_ENABLED",
            "COE_TIMEZONE", "COE_CRON", "COE_STATE_DIR", "COE_REPORT_RECIPIENT", "PUBLIC_BASE_URL",
            "COE_DASHBOARD_PATH",
        )
    }
    configuration["COE_SCHEDULE_REGISTERED"] = _truth("COE_SCHEDULE_REGISTERED")
    configuration["COE_DASHBOARD_AUTHENTICATED"] = True
    result = AuditOrchestrator(app_repo, state_root).run(
        release_root=release_root,
        trigger="scheduled-daily",
        build_id=os.environ.get("COE_BUILD_ID", f"scheduled-{app_head[:12]}"),
        baseline_commit=app_baseline,
        deterministic_commands=[
            {"name": "lpos-test-suite", "command": [python, "-m", "pytest", "-p", "no:cacheprovider", "-q", str(lpos_repo / "tests")], "cwd": str(lpos_repo), "env": {"PYTHONDONTWRITEBYTECODE": "1"}},
            {"name": "chip-state-migration", "command": ["npm", "run", "migrate"], "cwd": str(app_repo), "env": test_environment},
            {"name": "chip-test-suite", "command": ["npm", "run", "test"], "cwd": str(app_repo), "env": test_environment},
        ],
        source_repositories=[
            {"path": str(app_repo), "baseline_commit": app_baseline, "target_commit": app_head},
            {"path": str(lpos_repo), "baseline_commit": lpos_baseline, "target_commit": lpos_head},
        ],
        documentation_repo=lpos_repo,
        production=True,
        configuration=configuration,
        security_command=["node", "tests/coe-routes.test.js"],
        dependency_audit_command=["npm", "audit", "--omit=dev", "--audit-level=high", "--json"],
    )
    statuses = {item["gate_id"]: item["status"] for item in result["gates"]}
    if statuses.get("engineering-audit") == "pass":
        baseline_file.parent.mkdir(parents=True, exist_ok=True)
        temporary = baseline_file.with_suffix(".tmp")
        temporary.write_text(json.dumps({str(app_repo): app_head, str(lpos_repo): lpos_head}, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, baseline_file)
    token = os.environ.get("CHIP_OPERATOR_TOKEN")
    base_url = os.environ.get("PUBLIC_BASE_URL", "https://chip.listeningpost.ai").rstrip("/")
    delivery_status = "not-attempted"
    if token:
        _post_json(f"{base_url}/api/v1/coe/import", token, {"summary": result["summary"]})
        report = render_daily_report(result["summary"])
        delivery = _post_json(
            f"{base_url}/api/v1/coe/reports/{result['audit']['audit_id']}/deliver",
            token,
            {"report": report},
        )
        delivery_status = str(delivery.get("status", "unknown"))
    output = {
        "audit_id": result["audit"]["audit_id"],
        "status": result["audit"]["status"],
        "release_status": result["decision"]["status"],
        "gates": statuses,
        "report_delivery": delivery_status,
        "wake_decision": {"eligible": True, "wakeAgent": False, "reason_code": "DETERMINISTIC_COE_AUDIT", "decision_source": "deterministic-policy", "model_invoked": False},
    }
    print(json.dumps(output, sort_keys=True))
    return 0 if result["decision"]["status"] == "pass" and delivery_status == "delivered" else 1


if __name__ == "__main__":
    raise SystemExit(main())
