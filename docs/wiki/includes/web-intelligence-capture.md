---
title: Web Intelligence Capture
section: includes
order: 6
---

# Web Intelligence Capture

Web Intelligence Capture turns public web pages, GitHub repositories, PDFs, Office files, and approved seed directories into auditable source artifacts that LPOS can reason from.

It exists for one purpose: make web and document intake useful without letting scraping become an ungoverned data habit.

## What it does

- Captures public web pages into Markdown.
- Converts documents such as PDF, DOCX, HTML, and Office files into Markdown when they are inside an approved local file root or are approved public URLs.
- Records the original source, extraction method, timestamp, content hash, and confidence.
- Separates extracted facts from generated recommendations.
- Routes weak technical signals into SO-010 Technology Signals and the Evidence Ledger.
- Supports Chip source-site extraction and small-business launch prospect research.

## Adapter order

1. Use the installed Hermes managed web tools when they are enough.
2. Use Crawl4AI for local public web extraction canaries.
3. Use MarkItDown for local document conversion canaries.
4. Use Crawlee only for an approved queue-based crawl.
5. Treat browser agents, Scrapling, AutoScraper, and curl-impersonate as guarded fallback canaries, not defaults.

## Safety rules

Web Intelligence Capture fails closed.

Local file capture is denied unless the caller supplies an approved seed directory through `--allow-file-root` or `LPOS_WEB_INTEL_APPROVED_ROOT`.

It must not:

- bypass login gates
- bypass paywalls
- evade site-owner restrictions
- collect private data
- use anti-bot tooling to defeat access controls
- generate customer-site claims without source support

A failed extraction is a valid result when the source is restricted, empty, unsupported, or unverifiable.

## Chip workflows

For Chip, Web Intelligence Capture supports:

- pasted URL source extraction
- public business-site fact capture
- PDF, menu, brochure, and service-list intake
- prospect queue scoring for the wide launch plan
- missing-info prompts when the source is thin

Chip must keep source evidence attached to generated previews. If a service, location, price, credential, or claim is not found in the source, the preview should ask for the missing information instead of inventing it.

## Technology Signals workflow

For SO-010 Technology Signals, Web Intelligence Capture adds a structured intake path:

1. Normalize the source post, article, repository, or document.
2. Gather live metadata where available.
3. Score usefulness, license risk, implementation fit, overlap, and safety risk.
4. Decide implement now, canary, defer, or reject.
5. Record the decision and evidence.

## Evidence records

Each capture record should include:

- source URL or file path
- source type
- extraction adapter
- timestamp
- SHA-256 hash of normalized content
- byte count
- confidence
- blocked reason when capture is refused

## Related pages

- [SO-010: Technology Signals](/reference/so-010.html)
- [Everything LPOS includes](/includes/index.html)
- [How this wiki works](/documentation/how-the-wiki-works.html)
