---
title: Everything LPOS includes
section: includes
order: 1
---

# Everything LPOS includes

This section is the inventory: every module and capability in your installation, what it does, and where to read more. Everything here can be verified against your own system, `lpos doctor` counts it all, and the listing commands print it.

## The core (in every install)

- **The packaged operating specification**, the constitutional documents, the always-loaded Chip kernel, guild charters, specialist charters, craft standards, Standing Operation definitions, and benchmarks, shipped as package data and loaded on demand. Described throughout [Welcome & Concepts](/welcome/index.html).
- **The deterministic control plane**, state machines, materiality, routing, context compilation, approval and identity guards, review isolation, and the Standing Operation runner.
- **32 specialists across the guilds**, see the auto-generated [Specialists](/reference/specialists.html) page, built from the packaged specialist index. `lpos list-specialists` prints the same registry with full capability lists.
- **26 Standing Operations (SO-001 through SO-026)**, each has its own reference page, generated from the packaged workflow catalog and operation definitions, with its default schedule, requirements, specialists, and workflow steps. Start from [SO-001: Executive Brief](/reference/so-001.html) or browse the Reference section in the sidebar. `lpos list-workflows` prints the catalog.
- **53 benchmark fixtures**, covering the 32 specialists plus SO-001 through SO-021. Later Standing Operations use the first-production-run rule until dedicated benchmark fixtures are added; `lpos evals` runs the deterministic core evaluations against the fixed benchmark catalog.
- **17 executable JSON Schemas**, the machine contracts for every runtime entity, validated by `lpos validate-schemas`.
- **Packaged skills**, procedure documents the runtime loads on demand, including the load-bearing `independent-reviewer` and `quality-router`. See the auto-generated [Packaged skills](/reference/skills.html) page.
- **Transactional SQLite state with append-only events**, the audit backbone; see [Backups](/administration/backups.html) and [Reading agent output](/working-with/reading-agent-output.html).
- **Adapter boundaries**, the provider-neutral subprocess protocol for model hosts, plus the record-only consequential-action adapter and sandboxed local-file adapter for safe verification. See [Connector setup](/administration/connector-setup.html).
- **The CLI**, eleven commands from `version` to `doctor`; see the [CLI reference](/administration/cli-reference.html).

## The user-facing modules (4.1.0)

Release 4.1.0 adds three modules that every user receives, each with its own page:

- **[Hermes Project Dashboard](/includes/dashboard.html)**, your single pane of glass: what your agents are doing, in four buckets, with every file's disk location one click away. Runs locally at port 7373, started with the system.
- **[Connector Health Monitor](/includes/connector-health-monitor.html)**, an hourly audit of everything the system runs on: email, GitHub, cloud, MCP connectors, and self-built services. Emails you when something goes offline and when it recovers, and never spams in between.
- **[Skill Evolution](/includes/skill-evolution.html)**, LPOS improving its own skills from evidence, behind a held-out validation gate, staged for your review and never auto-adopted.

## How the Reference section stays honest

The per-operation pages, the specialist index, and the skills page in the Reference section are not hand-maintained: they are generated at build time by the wiki builder directly from the packaged system, the workflow catalog, the operation definitions, the specialist index, and the skill files. If the system changes, rebuilding the wiki changes those pages with it. See [How this wiki works](/documentation/how-the-wiki-works.html).

## Related pages

- [Specialists](/reference/specialists.html)
- [Packaged skills](/reference/skills.html)
- [Core concepts](/welcome/concepts.html)
- [How this wiki works](/documentation/how-the-wiki-works.html)

## The compliance layer (4.2.0)

- **SOC 2 Compliance Guild (GUILD-038)**, the codified Trust Services Criteria control catalog, the daily autonomous audit (SO-025), staged remediation in a test environment, and the compliance page. See [SOC 2 Compliance Guild](/includes/soc2-compliance.html).

## Web Intelligence Capture (4.2.1)

- **[Web Intelligence Capture](/includes/web-intelligence-capture.html)**, the governed intake layer for public web pages, GitHub repositories, PDFs, Office files, and approved seed directories. It normalizes sources into auditable Markdown and JSON records for Chip, Technology Signals, and Evidence Engine while failing closed on restricted sources.
