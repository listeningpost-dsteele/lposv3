---
title: Configuration
section: administration
order: 2
---

# Configuration

You want to know what is configurable in LPOS, where each setting lives, and — just as important — what is deliberately *not* configurable. LPOS separates three kinds of configuration: the packaged registry (ships with the release), deployment configuration (yours), and secrets (kept out of LPOS entirely).

## The packaged capability registry

`config/default_registry.json` (mirrored inside the package at `src/lpos_engine/config/`) is the 32-specialist capability registry: for each specialist, its canonical ID, name, guild, capabilities, craft standards, model class, and routing priority. The root and packaged copies must be identical — release verification fails otherwise — and the registry's `os_version` must match the release version. Treat it as part of the operating system: read it (or `lpos list-specialists`), do not hand-edit it.

The same applies to the workflow catalog (`src/lpos_engine/workflows/catalog.json`), the schemas, and the packaged specification: they are the release, versioned together as one unit.

## Deployment configuration

Deployment configuration is what makes an installation *yours*. It is established during [onboarding](/getting-started/onboarding.html) and covers:

- **Office identity** — `office.name` (default Chip) and `office.channel_identity`, the confirmed sending identity. Wherever any document says "Chip," the runtime reads your configured name, and outbound communications are signed with it.
- **Principal identity and verified channels** — your exact identity per channel, verified by a real round trip. Verified identities are what approval checking is built on.
- **Intent-to-channel mapping** — which channel carries each communication intent (Executive Decision, Operational Alert, Evidence, Status, Collaboration, Conversation). Confirmed during onboarding.
- **Model-class assignments** — which configured model adapter serves the `executive`, `routine`, `review`, and optional `local` classes. The review class prefers a different adapter from the creator.
- **Standing Operation activation** — which of SO-001 through SO-025 are enabled, with each activation or deferral recorded with its revisit condition.
- **Live action adapters** — which consequential-action adapters, if any, are registered and tested. Until one is, external actions stay record-only.
- **Module settings (4.1.0)** — the dashboard's Hermes root path and port (default 7373), written by onboarding from values it already knows; the monitor's alert recipient (defaults to the account LPOS is set up under) and per-connector criticality/mute annotations in its human-editable inventory.

Store only non-secret identifiers and policy choices in deployment configuration.

## Secrets

Secrets never enter LPOS. Provider tokens, email credentials, signing keys, and service secrets belong in your operating-system credential store or a deployment secret manager. By policy and by construction, credentials are excluded from constitutional documents, the Principal Model, the state database, context bundles, artifacts, events, and exports. The Connector Health Monitor likewise uses the credentials the system already holds, in place — nothing is copied into `~/.hermes/monitor/`.

## What is not configurable

The control plane's guarantees are not settings. There is no configuration that disables exact-action approval, allows silence to count as consent, lets a creator approve its own material work, or lets a model bypass a state machine. A prompt cannot waive a control-plane guard, and neither can a config file.

## Related pages

- [Onboarding walkthrough](/getting-started/onboarding.html)
- [Connector setup](/administration/connector-setup.html)
- [Specialists](/reference/specialists.html)
- [Backups](/administration/backups.html)
