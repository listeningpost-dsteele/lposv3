from __future__ import annotations

import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "tools" / "web_intelligence_capture.py"


def run_capture(source: str, out: Path, extra_args: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(TOOL), source, "--out", str(out)]
    if extra_args:
        command.extend(extra_args)
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def read_payload(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def serve_html(body: str) -> tuple[ThreadingHTTPServer, str]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            payload = body.encode("utf-8")
            self.send_response(200)
            self.send_header("content-type", "text/html; charset=utf-8")
            self.send_header("content-length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_port}/public"


def test_local_file_capture_is_blocked_without_approved_root(tmp_path: Path) -> None:
    source = tmp_path / "source.md"
    source.write_text("# Test Source\n\nThis fixture is not approved by default.\n", encoding="utf-8")
    out = tmp_path / "capture.json"

    proc = run_capture(str(source), out)

    assert proc.returncode == 2
    payload = read_payload(out)
    assert payload["status"] == "blocked"
    assert payload["blocked_reason"] == "local file capture requires approved root"
    assert payload["content"] == ""
    assert payload["sha256"] is None


def test_local_markdown_file_capture_records_hash_and_metadata_when_root_is_approved(tmp_path: Path) -> None:
    approved_root = tmp_path / "approved"
    approved_root.mkdir()
    source = approved_root / "source.md"
    source.write_text("# Test Source\n\nThis is public fixture content for Web Intelligence Capture.\n", encoding="utf-8")
    out = tmp_path / "capture.json"

    proc = run_capture(str(source), out, ["--allow-file-root", str(approved_root)])

    assert proc.returncode == 0, proc.stderr
    payload = read_payload(out)
    assert payload["status"] == "ok"
    assert payload["source_type"] == "file"
    assert payload["adapter"] in {"stdlib-text", "markitdown"}
    assert payload["sha256"]
    assert payload["bytes"] > 20
    assert "public fixture content" in payload["content"]


def test_local_file_outside_approved_root_is_blocked(tmp_path: Path) -> None:
    approved_root = tmp_path / "approved"
    approved_root.mkdir()
    source = tmp_path / "outside.md"
    source.write_text("# Outside\n\nThis file is outside the approved seed directory.\n", encoding="utf-8")
    out = tmp_path / "outside.json"

    proc = run_capture(str(source), out, ["--allow-file-root", str(approved_root)])

    assert proc.returncode == 2
    payload = read_payload(out)
    assert payload["status"] == "blocked"
    assert payload["blocked_reason"] == "local file outside approved root"
    assert payload["content"] == ""
    assert payload["sha256"] is None


def test_restricted_url_path_fails_closed(tmp_path: Path) -> None:
    out = tmp_path / "blocked.json"

    proc = run_capture("https://example.com/login", out)

    assert proc.returncode == 2
    payload = read_payload(out)
    assert payload["status"] == "blocked"
    assert payload["blocked_reason"] == "restricted path"
    assert payload["content"] == ""
    assert payload["sha256"] is None


def test_restricted_url_variants_fail_closed(tmp_path: Path) -> None:
    urls = [
        "https://example.com/auth",
        "https://example.com/wp-admin/index.php",
        "https://example.com/subscribe",
        "https://example.com/public?next=/account&auth=session",
    ]
    for index, url in enumerate(urls):
        out = tmp_path / f"blocked-{index}.json"
        proc = run_capture(url, out)
        payload = read_payload(out)
        assert proc.returncode == 2
        assert payload["status"] == "blocked"
        assert payload["blocked_reason"] == "restricted path"
        assert payload["content"] == ""
        assert payload["sha256"] is None


def test_local_html_conversion_strips_script(tmp_path: Path) -> None:
    approved_root = tmp_path / "approved"
    approved_root.mkdir()
    source = approved_root / "page.html"
    source.write_text(
        "<html><body><h1>Public Service Page</h1><script>secret()</script><p>Roof repair and HVAC service.</p></body></html>",
        encoding="utf-8",
    )
    out = tmp_path / "html.json"

    proc = run_capture(str(source), out, ["--allow-file-root", str(approved_root)])

    assert proc.returncode == 0, proc.stderr
    payload = read_payload(out)
    assert payload["status"] == "ok"
    assert "Public Service Page" in payload["content"]
    assert "Roof repair" in payload["content"]
    assert "secret()" not in payload["content"]


def test_long_restricted_file_content_fails_closed(tmp_path: Path) -> None:
    approved_root = tmp_path / "approved"
    approved_root.mkdir()
    source = approved_root / "long-paywall.md"
    source.write_text("# Long Page\n\nSubscribe to continue.\n" + ("public filler\n" * 500), encoding="utf-8")
    out = tmp_path / "long-paywall.json"

    proc = run_capture(str(source), out, ["--allow-file-root", str(approved_root)])

    assert proc.returncode == 2
    payload = read_payload(out)
    assert payload["status"] == "blocked"
    assert payload["blocked_reason"] == "restricted content marker"
    assert payload["content"] == ""
    assert payload["sha256"] is None


def test_long_login_required_html_fails_closed(tmp_path: Path) -> None:
    approved_root = tmp_path / "approved"
    approved_root.mkdir()
    source = approved_root / "long-login.html"
    source.write_text(
        "<html><body><h1>Login required</h1><p>" + ("filler " * 700) + "</p></body></html>",
        encoding="utf-8",
    )
    out = tmp_path / "long-login.json"

    proc = run_capture(str(source), out, ["--allow-file-root", str(approved_root)])

    assert proc.returncode == 2
    payload = read_payload(out)
    assert payload["status"] == "blocked"
    assert payload["blocked_reason"] == "restricted content marker"
    assert payload["content"] == ""
    assert payload["sha256"] is None


def test_long_restricted_http_content_fails_closed(tmp_path: Path) -> None:
    body = "<html><body><h1>Subscribe to continue</h1><p>" + ("filler " * 700) + "</p></body></html>"
    server, url = serve_html(body)
    out = tmp_path / "long-http-paywall.json"

    try:
        proc = run_capture(url, out)
    finally:
        server.shutdown()

    assert proc.returncode == 2
    payload = read_payload(out)
    assert payload["status"] == "blocked"
    assert payload["blocked_reason"] == "restricted content marker"
    assert payload["content"] == ""
    assert payload["sha256"] is None
