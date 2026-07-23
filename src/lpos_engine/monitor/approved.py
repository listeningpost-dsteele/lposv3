"""Admin-approved check templates and the execution trust boundary.

Security model (audit findings LPOS-03 / LPOS-04):

``<hermes root>/monitor/approved-checks.json`` is an **admin-owned** file.  It
is never written by discovery, never merged from agent-writable state, and is
the only place an executable check (``command``/``argv``) or a private-network
exemption (``private_network_approved``) can be defined.

Agent registrations (``state/services.json``,
``monitor/registered-services.json``) may only *reference* an approved
template by ``check_id`` and supply non-secret scalar parameters that fill
placeholders the template explicitly declares.  A registration that carries
its own executable definition (a ``command``, ``argv``, or ``type: command``
spec) is never executed: it is flagged in the inventory and reported with
status ``unknown`` and evidence ``unapproved check definition``.

File format::

    {
      "checks": {
        "report-api-health": {
          "type": "http_health",
          "url": "http://127.0.0.1:{port}/health",
          "parameters": ["port"],
          "private_network_approved": true,
          "description": "Health endpoint of the self-built report API"
        },
        "disk-free": {
          "type": "command",
          "argv": ["/usr/bin/df", "-P", "{mount}"],
          "parameters": ["mount"],
          "description": "df must exit 0 for the given mount"
        }
      }
    }

A top-level mapping without the ``"checks"`` wrapper is also accepted.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .inventory import hermes_root

APPROVED_FILENAME = "approved-checks.json"

#: Parameter values supplied by registrations must be non-secret scalars.
SCALAR_TYPES = (str, int, float, bool)

#: The only keys an agent registration's check spec may carry: a reference to
#: an approved template plus scalar parameters.  Anything else is an inline
#: executable definition and is refused.
REFERENCE_KEYS = frozenset({"check_id", "params"})

#: Evidence string used everywhere a non-approved executable definition is
#: refused (audit LPOS-03 closure wording).
UNAPPROVED = "unapproved check definition"

_PLACEHOLDER = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


class TemplateError(Exception):
    """A template reference could not be resolved into an executable spec."""


def approved_checks_path(root: Path | None = None) -> Path:
    """Path of the admin-owned template file (no directories are created)."""

    base = Path(root) if root is not None else hermes_root()
    return base / "monitor" / APPROVED_FILENAME


def load_approved_checks(root: Path | None = None) -> dict[str, dict[str, Any]]:
    """Load the admin-owned templates.  Missing/malformed file -> {}."""

    try:
        value = json.loads(approved_checks_path(root).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if isinstance(value, Mapping) and isinstance(value.get("checks"), Mapping):
        value = value["checks"]
    if not isinstance(value, Mapping):
        return {}
    return {
        str(check_id): dict(template)
        for check_id, template in value.items()
        if isinstance(template, Mapping)
    }


def is_reference_spec(spec: Any) -> bool:
    """True when a check spec is a pure {check_id, params} template reference."""

    if not isinstance(spec, Mapping):
        return False
    if not spec or set(spec) - REFERENCE_KEYS:
        return False
    check_id = spec.get("check_id")
    if not isinstance(check_id, str) or not check_id:
        return False
    params = spec.get("params")
    if params is None:
        return True
    if not isinstance(params, Mapping):
        return False
    return all(isinstance(v, SCALAR_TYPES) for v in params.values())


def _fill(value: Any, params: Mapping[str, str]) -> Any:
    """Substitute declared placeholders; reject any left unfilled."""

    if isinstance(value, str):
        def _sub(match: re.Match[str]) -> str:
            name = match.group(1)
            if name not in params:
                raise TemplateError(f"missing parameter {name!r}")
            return params[name]

        return _PLACEHOLDER.sub(_sub, value)
    if isinstance(value, list):
        return [_fill(item, params) for item in value]
    return value


def _instantiate(template: Mapping[str, Any], spec: Mapping[str, Any]) -> dict[str, Any]:
    declared = template.get("parameters") or []
    declared_names = {str(name) for name in declared} if isinstance(declared, list) else set()
    raw_params = spec.get("params") or {}
    if not isinstance(raw_params, Mapping):
        raise TemplateError("params must be a mapping of scalars")
    params: dict[str, str] = {}
    for name, value in raw_params.items():
        if str(name) not in declared_names:
            raise TemplateError(f"undeclared parameter {name!r}")
        if not isinstance(value, SCALAR_TYPES):
            raise TemplateError(f"parameter {name!r} must be a scalar")
        params[str(name)] = str(value)
    effective: dict[str, Any] = {}
    for key, value in template.items():
        if key in ("description", "parameters"):
            continue
        effective[key] = _fill(value, params)
    # Only an approved template may carry this marker; checks use it as a
    # defense-in-depth gate for executable checks.
    effective["_approved"] = True
    return effective


def resolve_execution_entry(
    entry: Mapping[str, Any], root: Path | None = None
) -> tuple[dict[str, Any] | None, str | None]:
    """Resolve an inventory entry into the entry that may actually execute.

    Returns ``(effective_entry, None)`` when execution is permitted, or
    ``(None, reason)`` when the entry must be reported as ``unknown`` with
    ``reason`` as evidence.  The effective entry's check spec:

    - is instantiated from the admin template when the entry references a
      ``check_id`` (only declared placeholders are filled, scalar params only);
    - never carries an inline ``command``/``argv`` definition — those are only
      valid inside approved templates;
    - only carries ``private_network_approved`` when the *template* set it —
      the flag is stripped from any inline spec (agent or hand-edited state
      cannot grant private-network egress);
    - carries ``_hermes_root`` so checks can validate secrets/executable paths
      against the right root without global state.
    """

    base = Path(root) if root is not None else hermes_root()
    if entry.get("unapproved_check"):
        return None, UNAPPROVED
    raw = entry.get("check")
    spec: Mapping[str, Any] = raw if isinstance(raw, Mapping) else {}

    if "check_id" in spec:
        if not is_reference_spec(spec):
            return None, UNAPPROVED
        template = load_approved_checks(base).get(str(spec["check_id"]))
        if template is None:
            return None, f"{UNAPPROVED}: unknown check_id {str(spec['check_id'])!r}"
        try:
            effective = _instantiate(template, spec)
        except TemplateError as exc:
            return None, f"{UNAPPROVED}: {exc}"
        effective["_hermes_root"] = str(base)
        return {**entry, "check": effective}, None

    if "command" in spec or "argv" in spec or str(spec.get("type", "")) == "command":
        return None, UNAPPROVED

    clean = {
        key: value
        for key, value in spec.items()
        if key not in ("private_network_approved", "_approved")
    }
    clean["_hermes_root"] = str(base)
    return {**entry, "check": clean}, None
