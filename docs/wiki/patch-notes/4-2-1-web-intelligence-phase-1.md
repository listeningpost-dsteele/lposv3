---
title: 4.2.1 Web Intelligence Capture Phase 1
section: patch-notes
order: 0.9
---

# 4.2.1 Web Intelligence Capture Phase 1

This patch adds the Phase 1 Web Intelligence Capture foundation.

## Added

- SO-026 Web Intelligence Capture as a governed Standing Operation.
- A user guide page for Web Intelligence Capture.
- A reference adapter for safe local capture canaries.
- Tests for adapter metadata, document conversion, and restricted-source refusal.

## Why it exists

Dan shared a thread of web-scraping repositories and approved Phase 1 implementation. The accepted lesson is not to install every scraper. The accepted lesson is to add one guarded capture layer that can normalize public web and document sources for Chip, LPOS, and Evidence Engine.

## Boundaries

This patch does not enable broad crawling by default. It does not bypass login, paywalls, robots constraints, or site-owner restrictions. It prepares local canaries and documentation for approval-gated use.

## Related pages

- [Web Intelligence Capture](/includes/web-intelligence-capture.html)
- [SO-010: Technology Signals](/reference/so-010.html)
- [Everything LPOS includes](/includes/index.html)
