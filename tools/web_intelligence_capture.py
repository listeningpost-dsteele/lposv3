#!/usr/bin/env python3
"""Guarded Web Intelligence Capture canary adapter.

Phase 1 goal: normalize public web and document sources into auditable records.
Optional adapters are used when installed:

- crawl4ai for web extraction
- markitdown for document conversion

The stdlib fallback is intentionally modest. It exists so the safety contract and
metadata path can be tested without making heavy crawler dependencies mandatory.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import hashlib
import html.parser
import json
import mimetypes
import os
from pathlib import Path
import re
import sys
import urllib.parse
import urllib.request

BLOCKED_SCHEMES = {"file", "ftp", "ssh", "sftp"}
RESTRICTED_MARKERS = (
    "login",
    "login required",
    "sign in",
    "sign-in",
    "authentication required",
    "auth required",
    "subscribe to continue",
    "subscription required",
    "paywall",
    "access denied",
    "forbidden",
)
RESTRICTED_URL_TERMS = (
    "/login",
    "/signin",
    "/sign-in",
    "/account",
    "/checkout",
    "/auth",
    "/authenticate",
    "/session",
    "/subscribe",
    "/wp-admin",
)
RESTRICTED_QUERY_TERMS = ("login", "signin", "auth", "session", "account", "checkout", "subscribe")


@dataclasses.dataclass
class CaptureRecord:
    source: str
    source_type: str
    adapter: str
    status: str
    timestamp: str
    sha256: str | None
    bytes: int
    confidence: str
    content: str
    blocked_reason: str | None = None

    def to_json(self) -> dict:
        return dataclasses.asdict(self)


class TextExtractor(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self.skip_depth += 1
        if tag in {"p", "br", "li", "h1", "h2", "h3", "section", "article"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self.skip_depth:
            self.skip_depth -= 1
        if tag in {"p", "li", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            cleaned = re.sub(r"\s+", " ", data).strip()
            if cleaned:
                self.parts.append(cleaned + " ")

    def text(self) -> str:
        raw = "".join(self.parts)
        lines = [re.sub(r"\s+", " ", line).strip() for line in raw.splitlines()]
        return "\n".join(line for line in lines if line)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def approved_file_roots(cli_roots: list[str] | None = None) -> list[Path]:
    raw_roots: list[str] = []
    if cli_roots:
        raw_roots.extend(cli_roots)
    env_root = os.environ.get("LPOS_WEB_INTEL_APPROVED_ROOT")
    if env_root:
        raw_roots.extend(part for part in env_root.split(os.pathsep) if part)
    roots: list[Path] = []
    for raw in raw_roots:
        roots.append(Path(raw).expanduser().resolve())
    return roots


def file_allowed(path: Path, roots: list[Path]) -> bool:
    resolved = path.expanduser().resolve()
    for root in roots:
        if resolved == root or root in resolved.parents:
            return True
    return False


def blocked(source: str, allowed_roots: list[Path] | None = None) -> str | None:
    parsed = urllib.parse.urlparse(source)
    if parsed.scheme in BLOCKED_SCHEMES:
        return f"blocked scheme: {parsed.scheme}"
    if parsed.scheme in {"http", "https"}:
        path = urllib.parse.unquote(parsed.path).lower()
        query = urllib.parse.unquote(parsed.query).lower()
        if any(term in path for term in RESTRICTED_URL_TERMS) or any(term in query for term in RESTRICTED_QUERY_TERMS):
            return "restricted path"
    if not parsed.scheme or len(parsed.scheme) == 1:
        roots = allowed_roots or []
        if not roots:
            return "local file capture requires approved root"
        if not file_allowed(Path(source), roots):
            return "local file outside approved root"
    return None


def classify(source: str) -> str:
    parsed = urllib.parse.urlparse(source)
    if parsed.scheme in {"http", "https"}:
        suffix = Path(parsed.path).suffix.lower()
        if suffix in {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx"}:
            return "document_url"
        return "web_url"
    return "file"


def try_markitdown(path_or_url: str) -> tuple[str, str] | None:
    try:
        from markitdown import MarkItDown  # type: ignore
    except Exception:
        return None
    md = MarkItDown()
    result = md.convert(path_or_url)
    text = getattr(result, "text_content", "") or ""
    return "markitdown", text.strip()


def convert_file(path: Path) -> tuple[str, str]:
    mark = try_markitdown(str(path))
    if mark and mark[1]:
        return mark
    text_types = {".txt", ".md", ".html", ".htm", ".csv", ".json"}
    if path.suffix.lower() in text_types:
        data = path.read_text(encoding="utf-8", errors="replace")
        if path.suffix.lower() in {".html", ".htm"}:
            parser = TextExtractor()
            parser.feed(data)
            return "stdlib-html", parser.text()
        return "stdlib-text", data.strip()
    raise ValueError("unsupported file type without MarkItDown")


def try_crawl4ai(url: str) -> tuple[str, str] | None:
    try:
        from crawl4ai import AsyncWebCrawler  # type: ignore
    except Exception:
        return None
    import asyncio

    async def run() -> str:
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url)
            return (getattr(result, "markdown", None) or getattr(result, "cleaned_html", "") or "").strip()

    text = asyncio.run(run())
    return "crawl4ai", text


def fetch_url(url: str) -> tuple[str, str]:
    crawl = try_crawl4ai(url)
    if crawl and crawl[1]:
        return crawl
    request = urllib.request.Request(url, headers={"User-Agent": "LPOS-Web-Intelligence-Canary/1.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        content_type = response.headers.get("content-type", "")
        data = response.read(2_000_000)
    text = data.decode("utf-8", errors="replace")
    if "html" in content_type or "<html" in text[:500].lower():
        parser = TextExtractor()
        parser.feed(text)
        return "stdlib-html", parser.text()
    return "stdlib-http", text.strip()


def capture(source: str, allowed_roots: list[Path] | None = None) -> CaptureRecord:
    reason = blocked(source, allowed_roots)
    timestamp = now_iso()
    source_type = classify(source)
    if reason:
        return CaptureRecord(source, source_type, "none", "blocked", timestamp, None, 0, "none", "", reason)

    try:
        if source_type == "file":
            adapter, content = convert_file(Path(source).expanduser())
        elif source_type == "document_url":
            mark = try_markitdown(source)
            if not mark:
                raise ValueError("document URL requires MarkItDown in Phase 1")
            adapter, content = mark
        else:
            adapter, content = fetch_url(source)
    except Exception as exc:
        return CaptureRecord(source, source_type, "none", "failed", timestamp, None, 0, "none", "", str(exc))

    lowered = content.lower()
    if not content.strip():
        return CaptureRecord(source, source_type, adapter, "failed", timestamp, None, 0, "none", "", "empty extraction")
    if any(marker in lowered for marker in RESTRICTED_MARKERS):
        return CaptureRecord(source, source_type, adapter, "blocked", timestamp, None, 0, "low", "", "restricted content marker")

    clean = content.strip()
    return CaptureRecord(source, source_type, adapter, "ok", timestamp, digest(clean), len(clean.encode("utf-8")), "medium", clean)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Capture public web or document source into an auditable JSON record")
    parser.add_argument("source")
    parser.add_argument("--out", type=Path)
    parser.add_argument(
        "--allow-file-root",
        action="append",
        default=[],
        help="Approved local file root. Local file capture is denied unless the source is under this root. Can be repeated.",
    )
    args = parser.parse_args(argv)
    record = capture(args.source, approved_file_roots(args.allow_file_root))
    payload = json.dumps(record.to_json(), indent=2, ensure_ascii=False)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0 if record.status == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
