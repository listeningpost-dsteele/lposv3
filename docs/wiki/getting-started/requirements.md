---
title: Requirements
section: getting-started
order: 1
---

# Requirements

You want to know whether LPOS will run on your machine and what arrives in the box. Short answer: if you have Python 3.11 or later, you are ready.

## System requirements

- **Python 3.11 or later.** This is the only hard requirement. The installer checks the version and stops with a clear error if it is too old.
- **A supported platform.** LPOS installs on macOS, Linux, and Windows. Each has its own one-line installer (see [Install LPOS](/getting-started/install.html)).
- **No network access needed to install.** The release bundle contains an offline wheel; the installer installs it with `--no-index`, so installation works on a machine with no internet connection.
- **No extra Python packages.** The core has zero runtime dependencies. (The optional `dev` extra adds `jsonschema` and `pytest` for development and full schema validation.)

## What is in the release bundle

The distribution is a single ZIP you extract into a new directory. Inside:

| Item | What it is |
|---|---|
| `INSTALL.sh` / `INSTALL.ps1` / `INSTALL.cmd` / `install.py` | One installer per platform, all wrapping the same Python installer |
| `Packages/lpos_os-4.0.0-py3-none-any.whl` | The offline wheel the installer installs |
| `src/lpos_engine/` | The engine source: control plane, packaged specification, schemas, workflows, benchmark fixtures |
| `schemas/` | Human-visible copy of the 17 executable JSON Schemas |
| `config/default_registry.json` | Human-visible copy of the 32-specialist capability registry |
| `docs/` | Architecture, security, adapter protocol, testing, and this wiki's sources (`docs/wiki/`) |
| `examples/` | A model-host example and a Standing Operation example |
| `tests/` | The full test suite (128 tests) |
| `RELEASE.json`, `RELEASE-MANIFEST.json`, `SHA256SUMS` | Release identity and file-integrity manifest |
| `verify_release.py` | Verifies the bundle before installation |

By the numbers, per the release manifest: 32 specialists, 21 Standing Operations, 53 benchmark fixtures, 17 schemas, SQLite state backend, append-only audit events, and a record-only default for external actions.

## What you do not need yet

You do not need model API keys, email credentials, or any connector to install and explore LPOS. The bundled adapters are deterministic verification components, and consequential actions default to record-only. Live model hosts and channel adapters come later, during [onboarding](/getting-started/onboarding.html) and [connector setup](/administration/connector-setup.html).

## Related pages

- [Install LPOS](/getting-started/install.html)
- [Onboarding walkthrough](/getting-started/onboarding.html)
- [What LPOS is](/welcome/index.html)
