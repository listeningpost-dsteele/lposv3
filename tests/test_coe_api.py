from __future__ import annotations

import http.client
import json
import threading
from pathlib import Path

from lpos_engine.coe import COEServer, _html
from lpos_engine.coe_runtime import dashboard_summary
from lpos_engine.coe_store import COEStore

LABELS = (
    "Overall Health Score",
    "Engineering Score",
    "Security Score",
    "Efficiency Score",
    "Cost Score",
    "Documentation Score",
    "Release Integrity",
    "Scheduler Health",
    "Wake-Agent Efficiency",
    "Prompt Drift",
    "Technical Debt",
    "Opportunity Backlog",
    "Release Readiness",
    "Top Risks",
    "Pending Approvals",
    "Recent Improvements",
    "Audit History",
    "Current Release Status",
)


def request(server: COEServer, path: str, token: str | None = None) -> tuple[int, dict[str, str], bytes]:
    host = str(server.server_address[0])
    port = int(server.server_address[1])
    connection = http.client.HTTPConnection(host, port, timeout=5)
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    connection.request("GET", path, headers=headers)
    response = connection.getresponse()
    body = response.read()
    result = response.status, {name.lower(): value for name, value in response.getheaders()}, body
    connection.close()
    return result


def test_dashboard_requires_auth_and_renders_all_labels(tmp_path: Path) -> None:
    store = COEStore(tmp_path)
    server = COEServer(("127.0.0.1", 0), store=store, operator_token="fixture-token", public_base_url="https://chip.listeningpost.ai")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, headers, body = request(server, "/dashboard/coe")
        assert status == 401
        assert headers["cache-control"].startswith("private, no-store")
        assert b"operator authentication required" in body

        status, headers, body = request(server, "/dashboard/coe", "fixture-token")
        assert status == 200
        html = body.decode("utf-8")
        for label in LABELS:
            assert label in html
        assert "unknown" in html
        assert "default-src 'none'" in headers["content-security-policy"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_ops_alias_redirects_to_canonical_path(tmp_path: Path) -> None:
    server = COEServer(("127.0.0.1", 0), store=COEStore(tmp_path), operator_token="fixture-token", public_base_url="https://chip.listeningpost.ai")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, headers, _ = request(server, "/ops/coe")
        assert status == 302
        assert headers["location"] == "/dashboard/coe"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_private_api_returns_no_store_and_unknown_not_green(tmp_path: Path) -> None:
    server = COEServer(("127.0.0.1", 0), store=COEStore(tmp_path), operator_token="fixture-token", public_base_url="https://chip.listeningpost.ai")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, headers, body = request(server, "/api/v1/coe/summary", "fixture-token")
        assert status == 200
        payload = json.loads(body)
        assert payload["status"] == "unknown"
        assert "score" not in payload
        assert headers["cache-control"].startswith("private, no-store")

        status, _, body = request(server, "/api/v1/operator/release-gate", "fixture-token")
        assert status == 200
        gate = json.loads(body)
        assert gate["status"] == "blocked"
        assert gate["ready_for_dan_approval"] is False
        assert gate["decision_reason_codes"] == ["DECISION_MISSING"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_html_escapes_persisted_values() -> None:
    summary = {
        "release_readiness": "blocked",
        "release_version": "<script>alert(1)</script>",
        "audit_id": "unknown",
        "generated_at": "now",
    }
    html = _html(summary)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
