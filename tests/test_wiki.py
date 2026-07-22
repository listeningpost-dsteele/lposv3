"""Tests for the LPOS User Guide wiki builder (tools/build_wiki.py)."""

from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"
WIKI_SOURCE = REPO_ROOT / "docs" / "wiki"

sys.path.insert(0, str(TOOLS_DIR))

import build_wiki  # noqa: E402


@pytest.fixture(scope="module")
def site(tmp_path_factory) -> Path:
    """Build the wiki once into a temporary directory."""
    out = tmp_path_factory.mktemp("wiki-build") / "wiki"
    rc = build_wiki.main(["--repo-root", str(REPO_ROOT), "--out", str(out)])
    assert rc == 0
    return out


@pytest.fixture(scope="module")
def version() -> str:
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def source_slugs() -> list[str]:
    return [
        p.relative_to(WIKI_SOURCE).with_suffix("").as_posix()
        for p in WIKI_SOURCE.rglob("*.md")
    ]


def site_pages(site: Path) -> list[Path]:
    return [p for p in site.rglob("*.html") if p.name != "index.html" or p.parent != site]


def test_build_runs_clean_into_tmp_dir(site: Path) -> None:
    assert site.is_dir()
    assert (site / "style.css").is_file()
    assert (site / "app.js").is_file()
    assert (site / "index.html").is_file()


def test_every_source_page_lands_in_site(site: Path) -> None:
    slugs = source_slugs()
    assert len(slugs) >= 18, "expected a genuinely complete guide"
    for slug in slugs:
        assert (site / (slug + ".html")).is_file(), f"missing page for {slug}"


def test_generated_reference_pages_present(site: Path) -> None:
    catalog = json.loads(
        (REPO_ROOT / "src" / "lpos_engine" / "workflows" / "catalog.json").read_text(
            encoding="utf-8"
        )
    )
    for entry in catalog["operations"]:
        page = site / "reference" / (entry["so_id"].lower() + ".html")
        assert page.is_file(), f"missing generated page for {entry['so_id']}"
        text = page.read_text(encoding="utf-8")
        assert entry["default_schedule"] in text
    assert (site / "reference" / "specialists.html").is_file()
    assert (site / "reference" / "skills.html").is_file()
    skills_html = (site / "reference" / "skills.html").read_text(encoding="utf-8")
    for skill_dir in (REPO_ROOT / "src" / "lpos_engine" / "spec" / "skills").iterdir():
        if (skill_dir / "SKILL.md").is_file():
            assert skill_dir.name in skills_html


def test_nav_and_search_index_include_all_pages(site: Path) -> None:
    index = json.loads((site / "search-index.json").read_text(encoding="utf-8"))
    urls = {entry["url"] for entry in index}
    all_pages = {
        p.relative_to(site).as_posix()
        for p in site.rglob("*.html")
        if p != site / "index.html"
    }
    assert urls == all_pages
    for entry in index:
        assert entry["title"]
        assert entry["section"]
        assert entry["text"]
    # The sidebar on every page links to every page.
    welcome = (site / "welcome" / "index.html").read_text(encoding="utf-8")
    for url in urls:
        assert url in welcome, f"nav is missing a link to {url}"


def test_combined_single_file_guide_generated(site: Path) -> None:
    combined = site.parent / "LPOS-User-Guide.html"
    assert combined.is_file()
    text = combined.read_text(encoding="utf-8")
    index = json.loads((site / "search-index.json").read_text(encoding="utf-8"))
    for entry in index:
        anchor = "page-" + entry["url"][: -len(".html")].replace("/", "-")
        assert f'id="{anchor}"' in text, f"combined guide missing {entry['url']}"
    # Combined internal links point at in-document anchors, not site files.
    assert 'href="/' not in text


def test_internal_links_resolve(site: Path) -> None:
    href_re = re.compile(r'href="([^"]+)"')
    broken: list[str] = []
    for page in site.rglob("*.html"):
        for href in href_re.findall(page.read_text(encoding="utf-8")):
            if href.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = href.split("#", 1)[0]
            if not target:
                continue
            resolved = (page.parent / target).resolve()
            if not resolved.is_file():
                broken.append(f"{page.relative_to(site)} -> {href}")
    assert not broken, "broken internal links:\n" + "\n".join(broken)


def test_version_badge_matches_pyproject(site: Path, version: str) -> None:
    badge = f"LPOS v{version}"
    for page in site.rglob("*.html"):
        if page == site / "index.html":
            continue  # root redirect page has no chrome
        assert badge in page.read_text(encoding="utf-8"), f"no version badge on {page}"
    combined = site.parent / "LPOS-User-Guide.html"
    assert badge in combined.read_text(encoding="utf-8")


def test_source_pages_have_valid_frontmatter() -> None:
    known_sections = {slug for slug, _ in build_wiki.SECTIONS}
    for path in WIKI_SOURCE.rglob("*.md"):
        meta, body = build_wiki.parse_frontmatter(path.read_text(encoding="utf-8"))
        assert meta.get("title"), f"{path} has no title"
        assert meta.get("section") in known_sections, f"{path} has unknown section"
        assert body.strip(), f"{path} is empty"
