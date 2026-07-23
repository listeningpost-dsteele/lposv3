"""Connector inventory: automatic discovery merged with human edits.

The inventory lives at ``<hermes root>/monitor/inventory.json`` and is the
single human-editable list of everything the monitor watches.  Discovery scans
the Hermes state tree defensively (missing directories and malformed files are
simply skipped) and merges what it finds into the existing inventory without
ever overwriting a field the owner has edited and without silently dropping
entries that discovery no longer sees.

Sources scanned:

- ``<root>/mcp-tokens/`` and ``<root>/gateway/`` — registered connectors; each
  file or directory name becomes a connector id.
- ``<root>/platforms/`` — platform integrations (email, VCS, cloud, ...).
- ``<root>/state/services.json`` or ``<root>/monitor/registered-services.json``
  — the registration hook for self-built services.  Any agent that stands up a
  service appends ``{id, name, kind, check, criticality}`` there.
- the repo's ``config/default_registry.json`` — if it declares external
  connectors under a ``connectors`` / ``external_connectors`` key (the stock
  registry declares none, so it usually contributes nothing).

Trust boundary (audit LPOS-03): registration files are agent-writable, so a
registered ``check`` may ONLY be a reference to an admin-approved template —
``{"check_id": "<id in monitor/approved-checks.json>", "params": {...scalars}}``.
A registration carrying its own executable definition (command, argv, url,
host, an inline ``type``, ...) is sanitised here: its check is dropped and the
entry is flagged ``unapproved_check`` so the audit reports it ``unknown`` with
evidence ``unapproved check definition`` instead of ever executing it.  The
merge only ever fills fields missing from the owner's inventory, so agent
state can neither override owner edits nor approved templates.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

KINDS = ("email", "vcs", "cloud", "mcp", "self_built", "other")
CRITICALITIES = ("critical", "informational")

_KIND_HINTS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("github", "gitlab", "bitbucket", "git"), "vcs"),
    (("smtp", "imap", "mail", "gmail", "outlook", "email"), "email"),
    (("aws", "gcp", "azure", "cloud", "s3", "digitalocean"), "cloud"),
)


def hermes_root() -> Path:
    """Resolve the Hermes state root (env LPOS_HERMES_ROOT, default ~/.hermes)."""

    return Path(os.environ.get("LPOS_HERMES_ROOT", "~/.hermes")).expanduser()


def monitor_dir(root: Path | None = None) -> Path:
    from ..store import secure_mkdir

    directory = (Path(root) if root is not None else hermes_root()) / "monitor"
    return secure_mkdir(directory)


def inventory_path(root: Path | None = None) -> Path:
    return monitor_dir(root) / "inventory.json"


def _guess_kind(name: str, default: str) -> str:
    lowered = name.lower()
    for needles, kind in _KIND_HINTS:
        if any(needle in lowered for needle in needles):
            return kind
    return default


def _entry(
    entry_id: str,
    name: str,
    kind: str,
    *,
    check: Mapping[str, Any] | None = None,
    criticality: str = "critical",
    description: str = "",
) -> dict[str, Any]:
    return {
        "id": entry_id,
        "name": name,
        "kind": kind if kind in KINDS else "other",
        "check": dict(check) if check else {},
        "criticality": criticality if criticality in CRITICALITIES else "critical",
        "description": description,
        "muted": False,
    }


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _scan_names(directory: Path) -> list[str]:
    if not directory.is_dir():
        return []
    names = []
    try:
        for item in sorted(directory.iterdir(), key=lambda p: p.name):
            if item.name.startswith("."):
                continue
            names.append(item.stem if item.is_file() else item.name)
    except OSError:
        return []
    return names


def _sanitized_check(raw_check: Any) -> tuple[dict[str, Any], bool]:
    """Reduce an agent-supplied check to an approved-template reference.

    Returns ``(check, unapproved)``.  Only ``{"check_id": str, "params":
    {scalars}}`` survives; anything else (inline command/argv/url/type/... —
    any executable definition) is dropped and flagged so the audit reports
    ``unknown`` / ``unapproved check definition`` rather than executing it.
    """

    from . import approved as approved_module  # local import: avoid cycle at load

    if raw_check in (None, {}) or not isinstance(raw_check, Mapping):
        return {}, False
    if approved_module.is_reference_spec(raw_check):
        check: dict[str, Any] = {"check_id": str(raw_check["check_id"])}
        params = raw_check.get("params")
        if isinstance(params, Mapping) and params:
            check["params"] = {str(k): v for k, v in params.items()}
        return check, False
    return {}, True


def _service_entries(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, Mapping):
        value = value.get("services", [])
    if not isinstance(value, list):
        return []
    entries = []
    for raw in value:
        if not isinstance(raw, Mapping) or not raw.get("id"):
            continue
        entry_id = str(raw["id"])
        check, unapproved = _sanitized_check(raw.get("check"))
        entry = _entry(
            entry_id,
            str(raw.get("name", entry_id)),
            str(raw.get("kind", "self_built")),
            check=check,
            criticality=str(raw.get("criticality", "critical")),
            description=str(raw.get("description", "")),
        )
        if unapproved:
            entry["unapproved_check"] = True
        entries.append(entry)
    return entries


def _repo_config_entries(repo_config: Path | None) -> list[dict[str, Any]]:
    if repo_config is None:
        return []
    value = _load_json(Path(repo_config))
    if not isinstance(value, Mapping):
        return []
    declared = value.get("connectors") or value.get("external_connectors") or []
    return _service_entries({"services": declared})


def discover(root: Path | None = None, repo_config: Path | None = None) -> list[dict[str, Any]]:
    """Assemble the auto-discovered inventory from the Hermes state tree."""

    base = Path(root) if root is not None else hermes_root()
    found: list[dict[str, Any]] = []

    for name in _scan_names(base / "mcp-tokens"):
        found.append(
            _entry(
                f"mcp:{name}",
                name,
                _guess_kind(name, "mcp"),
                description=f"MCP connector registered under mcp-tokens/{name}",
            )
        )
    for name in _scan_names(base / "gateway"):
        found.append(
            _entry(
                f"gateway:{name}",
                name,
                _guess_kind(name, "mcp"),
                description=f"Gateway connector registered under gateway/{name}",
            )
        )
    for name in _scan_names(base / "platforms"):
        found.append(
            _entry(
                f"platform:{name}",
                name,
                _guess_kind(name, "other"),
                description=f"Platform integration registered under platforms/{name}",
            )
        )

    for candidate in (base / "state" / "services.json", base / "monitor" / "registered-services.json"):
        found.extend(_service_entries(_load_json(candidate)))

    found.extend(_repo_config_entries(repo_config))

    # De-duplicate by id, first occurrence wins.
    seen: dict[str, dict[str, Any]] = {}
    for entry in found:
        seen.setdefault(entry["id"], entry)
    return list(seen.values())


def load_inventory(root: Path | None = None) -> list[dict[str, Any]]:
    value = _load_json(inventory_path(root))
    if isinstance(value, Mapping):
        value = value.get("connectors", [])
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping) and item.get("id")]


def save_inventory(entries: list[dict[str, Any]], root: Path | None = None) -> Path:
    path = inventory_path(root)
    payload = {"connectors": entries}
    tmp = path.with_suffix(".json.tmp")
    from ..store import harden_file_mode, secure_create_file

    secure_create_file(tmp)  # LPOS-15
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    harden_file_mode(path)
    return path


def merge(
    existing: list[dict[str, Any]], discovered: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Merge discovered entries into the existing inventory.

    User edits always win: for entries the owner already has, discovery only
    fills in fields that are missing.  Entries no longer discovered are kept
    (never silently dropped); mute flags and criticality survive untouched.
    """

    by_id: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for raw in existing:
        entry = dict(raw)
        entry_id = str(entry["id"])
        if entry_id not in by_id:
            by_id[entry_id] = entry
            order.append(entry_id)
    for fresh in discovered:
        entry_id = str(fresh["id"])
        current = by_id.get(entry_id)
        if current is None:
            by_id[entry_id] = dict(fresh)
            order.append(entry_id)
        else:
            for key, value in fresh.items():
                current.setdefault(key, value)
    merged = [by_id[entry_id] for entry_id in order]
    for entry in merged:  # normalise required fields without clobbering edits
        entry.setdefault("name", entry["id"])
        entry.setdefault("kind", "other")
        entry.setdefault("check", {})
        entry.setdefault("criticality", "critical")
        entry.setdefault("muted", False)
    return merged


def refresh_inventory(
    root: Path | None = None, repo_config: Path | None = None
) -> list[dict[str, Any]]:
    """Discover, merge with the on-disk inventory, persist, and return it."""

    merged = merge(load_inventory(root), discover(root, repo_config))
    save_inventory(merged, root)
    return merged
