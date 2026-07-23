---
title: How this wiki works
section: documentation
order: 1
---

# How this wiki works

This page is the docs about the docs. It ships to every user because some users write patches, and the guide's central promise — that it stays current — depends on patch authors knowing the mechanism.

## Source of truth

The guide's sources live in the repository, next to the code they describe:

```text
docs/wiki/<section>/<page>.md
```

Each page is one Markdown file with a small frontmatter block:

```text
---
title: Install LPOS
section: getting-started
order: 2
---
```

`section` places the page in the sidebar tree, `order` sorts it within its section, and the file path fixes the page's stable, human-readable URL (`docs/wiki/getting-started/install.md` becomes `getting-started/install.html`). Internal links are written site-root-relative (`/getting-started/install.html`) and the builder rewrites them per page.

The style rules: written for an LPOS user, not a developer; every how-to starts from what the user wants to accomplish; every page ends with related pages; and every claim comes from the repository — if a feature cannot be located in the repo, it does not go in the guide.

## Building the site

```bash
python tools/build_wiki.py
```

The builder is a stdlib-only Python script — no dependencies to install. It converts the pages to a static site at `dist/wiki/` (sidebar navigation, client-side full-text search, version badge on every page, dark-mode aware, mobile-readable) and also writes `dist/LPOS-User-Guide.html`, the entire guide as one printable file for release artifacts. The version badge is read from `pyproject.toml`, so the guide always states which release it reflects. `--out DIR` (or `LPOS_WIKI_OUT`) redirects the output.

Part of the site is *generated from the system itself* at build time: one reference page per Standing Operation (from the packaged workflow catalog and operation definitions), the specialist index page (from the packaged specialist index), and the skills page (from each packaged `SKILL.md`'s frontmatter). Those pages cannot drift from the system, because they are derived from it on every build.

The build is tested: `tests/test_wiki.py` verifies that the build runs clean, every source page lands in the site, navigation and the search index include every page, internal links resolve, the combined guide is generated, and the version badge matches `pyproject.toml`.

## The docs gate: patches must update the guide

This is the mechanism that keeps the guide alive, and it is enforced, not hoped for:

1. **Every patch that adds or changes user-facing behavior must include its docs** — updates to the affected pages in `docs/wiki/`, plus a new entry in the patch-notes section.
2. **A patch with no user-facing change must say so explicitly.** Declaring "no user-facing change" is the only accepted alternative to a docs update; an empty docs section fails the patch.
3. **The wiki rebuild is part of the release pipeline.** When a release ships, `python tools/build_wiki.py` regenerates the site and the combined single-file guide as release artifacts, so one patch equals one guide update.

For patch authors, the practical checklist: edit or add the affected pages under `docs/wiki/`, add `docs/wiki/patch-notes/<version>.md` (and link it from the patch-notes index, newest first), run `python tools/build_wiki.py` locally to see the result, and run the wiki tests.

## The safety net: the weekly drift audit

Gates get dodged. **SO-024 Documentation Drift Audit** runs weekly and diffs what actually exists in the repository — modules, Standing Operations, connectors, skills — against the pages in this guide, and files a task for anything undocumented. Combined with the generated reference pages (which cannot drift by construction), the guide's failure mode changes from "quietly stale" to "a task exists naming exactly what is missing."

## Related pages

- [Patch notes](/patch-notes/index.html)
- [Everything LPOS includes](/includes/index.html)
- [Upgrading](/administration/upgrading.html)
