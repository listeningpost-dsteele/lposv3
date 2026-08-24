"""LPOS v4.8.3 executable guild model routing.

The routing table is no longer advisory. managed-run fails closed unless the
Hermes command used for creator/reviewer phases matches the lane required by
the creator specialist's guild (or model_class fallback).

Other operators can override the table without editing source:
  - env LPOS_MODEL_ROUTING_CONFIG=/path/to/model_routing.json
  - file ~/.hermes/lpos-model-routing.json
  - env LPOS_MODEL_ROUTING_ENFORCE=0 to disable (emergency only)

Wrappers are expected on PATH or under ~/.hermes/bin (see guild-model-routing).
"""

from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

ROUTING_VERSION = "1.4.0-lpos483"

_CONFIG_ENV = "LPOS_MODEL_ROUTING_CONFIG"
_ENFORCE_ENV = "LPOS_MODEL_ROUTING_ENFORCE"
_USER_OVERRIDE = Path.home() / ".hermes" / "lpos-model-routing.json"


@dataclass(frozen=True)
class Lane:
    """One executable model lane."""

    wrapper: str
    provider: str
    model: str
    family: str
    fallback_wrapper: str | None = None
    source: str = "guild"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RouteDecision:
    """Result of resolving or validating a managed-run hermes command."""

    ok: bool
    enforce: bool
    guild: str
    specialist_id: str
    model_class: str
    required: Lane | None
    requested_command: str
    bound_command: str | None = None
    gaps: list[str] = field(default_factory=list)
    detail: str = ""
    routing_version: str = ROUTING_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "enforce": self.enforce,
            "guild": self.guild,
            "specialist_id": self.specialist_id,
            "model_class": self.model_class,
            "required": self.required.to_dict() if self.required else None,
            "requested_command": self.requested_command,
            "bound_command": self.bound_command,
            "gaps": list(self.gaps),
            "detail": self.detail,
            "routing_version": self.routing_version,
        }


def _packaged_config_path() -> Path:
    return Path(__file__).resolve().parent / "config" / "model_routing.json"


def load_routing_config(path: Path | None = None) -> dict[str, Any]:
    """Load routing config: explicit path, env, user override, then packaged default."""
    candidates: list[Path] = []
    if path is not None:
        candidates.append(path.expanduser())
    env_path = os.environ.get(_CONFIG_ENV, "").strip()
    if env_path:
        candidates.append(Path(env_path).expanduser())
    if _USER_OVERRIDE.exists():
        candidates.append(_USER_OVERRIDE)
    candidates.append(_packaged_config_path())

    last_error: Exception | None = None
    for candidate in candidates:
        try:
            if candidate.is_file():
                data = json.loads(candidate.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    raise ValueError(f"routing config must be a JSON object: {candidate}")
                data["_loaded_from"] = str(candidate)
                return data
        except Exception as exc:  # noqa: BLE001 - surface as last_error
            last_error = exc
            continue
    if last_error is not None:
        raise last_error
    raise FileNotFoundError("no model routing config found")


def enforcement_enabled(config: dict[str, Any] | None = None) -> bool:
    """Whether managed-run must obey the routing table."""
    env = os.environ.get(_ENFORCE_ENV, "").strip().lower()
    if env in {"0", "false", "no", "off"}:
        return False
    if env in {"1", "true", "yes", "on"}:
        return True
    cfg = config if config is not None else load_routing_config()
    return bool(cfg.get("enforce", True))


def model_family(name: str) -> str:
    """Map a model/provider/wrapper string to a coarse family bucket."""
    text = (name or "").lower()
    if any(tok in text for tok in ("glm", "zai")):
        return "glm"
    if any(tok in text for tok in ("kimi", "k3", "k2", "moonshot")):
        return "kimi"
    if any(tok in text for tok in ("gpt", "codex", "openai")):
        return "gpt"
    if any(tok in text for tok in ("grok", "xai")):
        return "xai"
    if any(tok in text for tok in ("qwen", "laguna", "deepseek", "framework", "ollama")):
        return "framework"
    return text or "unknown"


def _lane_from_mapping(raw: dict[str, Any], *, source: str) -> Lane:
    wrapper = str(raw.get("wrapper") or "").strip()
    if not wrapper:
        raise ValueError("lane mapping missing wrapper")
    provider = str(raw.get("provider") or "").strip()
    model = str(raw.get("model") or "").strip()
    family = str(raw.get("family") or model_family(wrapper + " " + model + " " + provider)).strip()
    fallback = raw.get("fallback_wrapper")
    return Lane(
        wrapper=wrapper,
        provider=provider,
        model=model,
        family=family,
        fallback_wrapper=str(fallback).strip() if fallback else None,
        source=source,
    )


def resolve_guild_lane(
    guild: str,
    *,
    model_class: str | None = None,
    config: dict[str, Any] | None = None,
) -> Lane:
    """Resolve the required lane for a guild, falling back to model_class defaults."""
    cfg = config if config is not None else load_routing_config()
    guilds = cfg.get("guild_lanes") or {}
    if not isinstance(guilds, dict):
        raise ValueError("guild_lanes must be an object")

    key = (guild or "").strip()
    # Accept short names without GUILD- prefix
    if key and key not in guilds and not key.startswith("GUILD-"):
        alt = f"GUILD-{key}"
        if alt in guilds:
            key = alt
    if key in guilds and isinstance(guilds[key], dict):
        return _lane_from_mapping(guilds[key], source="guild")

    classes = cfg.get("model_class_defaults") or {}
    mc = (model_class or "executive").strip().lower()
    if mc in classes and isinstance(classes[mc], dict):
        return _lane_from_mapping(classes[mc], source="model_class")
    # last resort: executive default if present
    if "executive" in classes and isinstance(classes["executive"], dict):
        return _lane_from_mapping(classes["executive"], source="model_class_fallback")
    raise KeyError(f"no lane for guild={guild!r} model_class={model_class!r}")


def resolve_specialist_lane(
    *,
    specialist_id: str,
    guild: str,
    model_class: str,
    config: dict[str, Any] | None = None,
) -> Lane:
    """Resolve lane for a specialist (guild first, then model_class)."""
    _ = specialist_id  # reserved for future per-specialist overrides
    return resolve_guild_lane(guild, model_class=model_class, config=config)


def _command_basename(command: str) -> str:
    text = (command or "").strip()
    if not text:
        return ""
    # keep absolute paths intact for existence checks, basename for matching
    return Path(text).name


def _is_bare_hermes(command: str, config: dict[str, Any]) -> bool:
    bare = config.get("bare_hermes_names") or ["hermes", "hermes-agent"]
    name = _command_basename(command).lower()
    return name in {str(item).lower() for item in bare}


def find_wrapper_executable(
    wrapper: str,
    *,
    config: dict[str, Any] | None = None,
) -> str | None:
    """Resolve a wrapper name to an executable path, or None if missing."""
    cfg = config if config is not None else load_routing_config()
    wrapper = (wrapper or "").strip()
    if not wrapper:
        return None
    # Absolute / relative path already provided
    as_path = Path(wrapper).expanduser()
    if as_path.is_file() and os.access(as_path, os.X_OK):
        return str(as_path.resolve())

    which = shutil.which(wrapper)
    if which:
        return which

    for raw_dir in cfg.get("wrapper_bin_dirs") or []:
        directory = Path(str(raw_dir)).expanduser()
        candidate = directory / wrapper
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate.resolve())
    return None


def command_matches_lane(command: str, lane: Lane, *, config: dict[str, Any] | None = None) -> bool:
    """True if the hermes command is the required wrapper (or equivalent path)."""
    cfg = config if config is not None else load_routing_config()
    if not command or not lane:
        return False
    base = _command_basename(command)
    if base == lane.wrapper or command.rstrip("/").endswith("/" + lane.wrapper):
        return True
    if lane.fallback_wrapper and (
        base == lane.fallback_wrapper or command.rstrip("/").endswith("/" + lane.fallback_wrapper)
    ):
        return True
    # If user passed absolute path to the same resolved wrapper, accept it
    required = find_wrapper_executable(lane.wrapper, config=cfg)
    if required:
        try:
            if Path(command).expanduser().resolve() == Path(required).resolve():
                return True
        except OSError:
            pass
    if lane.fallback_wrapper:
        fb = find_wrapper_executable(lane.fallback_wrapper, config=cfg)
        if fb:
            try:
                if Path(command).expanduser().resolve() == Path(fb).resolve():
                    return True
            except OSError:
                pass
    return False


def bind_hermes_command(
    *,
    specialist_id: str,
    guild: str,
    model_class: str,
    hermes_command: str,
    config: dict[str, Any] | None = None,
    authorize_override: bool = False,
) -> RouteDecision:
    """Validate (and optionally auto-bind) hermes_command for a specialist.

    Rules when enforce=True:
      1. Bare `hermes` is auto-bound to the guild wrapper if auto_bind_default_hermes
         is true and the wrapper exists; else fail with hermes_command_unrouted.
      2. Explicit command must match the guild lane (wrapper basename or path).
      3. authorize_override=True allows a non-matching command (records gap warning
         style detail but ok=True) for break-glass ops.
    """
    cfg = config if config is not None else load_routing_config()
    enforce = enforcement_enabled(cfg)
    requested = (hermes_command or "hermes").strip() or "hermes"

    try:
        lane = resolve_specialist_lane(
            specialist_id=specialist_id,
            guild=guild,
            model_class=model_class,
            config=cfg,
        )
    except Exception as exc:  # noqa: BLE001
        decision = RouteDecision(
            ok=not enforce,
            enforce=enforce,
            guild=guild,
            specialist_id=specialist_id,
            model_class=model_class,
            required=None,
            requested_command=requested,
            gaps=["model_lane_unresolved"],
            detail=str(exc),
        )
        return decision

    gaps: list[str] = []
    bound = requested
    detail = "lane ok"

    if not enforce:
        return RouteDecision(
            ok=True,
            enforce=False,
            guild=guild,
            specialist_id=specialist_id,
            model_class=model_class,
            required=lane,
            requested_command=requested,
            bound_command=requested,
            gaps=[],
            detail="enforcement disabled",
        )

    if _is_bare_hermes(requested, cfg):
        if cfg.get("auto_bind_default_hermes", True):
            resolved = find_wrapper_executable(lane.wrapper, config=cfg)
            if resolved is None and lane.fallback_wrapper:
                resolved = find_wrapper_executable(lane.fallback_wrapper, config=cfg)
            if resolved is None:
                gaps.append("required_wrapper_missing")
                detail = (
                    f"guild {guild} requires wrapper {lane.wrapper} "
                    f"(model {lane.model}); bare 'hermes' is not allowed. "
                    f"Install the wrapper on PATH or pass --hermes-command explicitly."
                )
                return RouteDecision(
                    ok=False,
                    enforce=True,
                    guild=guild,
                    specialist_id=specialist_id,
                    model_class=model_class,
                    required=lane,
                    requested_command=requested,
                    bound_command=None,
                    gaps=gaps,
                    detail=detail,
                )
            bound = resolved
            detail = f"auto-bound bare hermes -> {bound}"
        else:
            gaps.append("hermes_command_unrouted")
            detail = (
                f"bare hermes forbidden for guild {guild}; "
                f"pass --hermes-command {lane.wrapper}"
            )
            return RouteDecision(
                ok=False,
                enforce=True,
                guild=guild,
                specialist_id=specialist_id,
                model_class=model_class,
                required=lane,
                requested_command=requested,
                bound_command=None,
                gaps=gaps,
                detail=detail,
            )
    elif not command_matches_lane(requested, lane, config=cfg):
        if authorize_override:
            detail = (
                f"override authorized: requested {requested} does not match "
                f"required {lane.wrapper} for {guild}"
            )
            return RouteDecision(
                ok=True,
                enforce=True,
                guild=guild,
                specialist_id=specialist_id,
                model_class=model_class,
                required=lane,
                requested_command=requested,
                bound_command=requested,
                gaps=["model_lane_override"],
                detail=detail,
            )
        gaps.append("hermes_command_lane_mismatch")
        detail = (
            f"guild {guild} requires --hermes-command {lane.wrapper} "
            f"(provider={lane.provider} model={lane.model}); got {requested!r}. "
            f"This is the enforcement gate that stops ambient-default credit burn."
        )
        return RouteDecision(
            ok=False,
            enforce=True,
            guild=guild,
            specialist_id=specialist_id,
            model_class=model_class,
            required=lane,
            requested_command=requested,
            bound_command=None,
            gaps=gaps,
            detail=detail,
        )
    else:
        # Explicit matching command: prefer resolved absolute path when available
        resolved = find_wrapper_executable(requested, config=cfg)
        if resolved:
            bound = resolved
        detail = f"explicit lane match: {bound}"

    # Final existence check on bound command
    if shutil.which(bound) is None and not Path(bound).expanduser().is_file():
        gaps.append("hermes_cli_missing")
        return RouteDecision(
            ok=False,
            enforce=True,
            guild=guild,
            specialist_id=specialist_id,
            model_class=model_class,
            required=lane,
            requested_command=requested,
            bound_command=bound,
            gaps=gaps,
            detail=f"bound command not executable: {bound}",
        )

    return RouteDecision(
        ok=True,
        enforce=True,
        guild=guild,
        specialist_id=specialist_id,
        model_class=model_class,
        required=lane,
        requested_command=requested,
        bound_command=bound,
        gaps=gaps,
        detail=detail,
    )


def list_routes(config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return the full routing table for CLI/status."""
    cfg = config if config is not None else load_routing_config()
    guild_lanes = {}
    for guild, raw in (cfg.get("guild_lanes") or {}).items():
        if isinstance(raw, dict):
            try:
                guild_lanes[guild] = _lane_from_mapping(raw, source="guild").to_dict()
            except ValueError:
                guild_lanes[guild] = raw
    class_defaults = {}
    for mc, raw in (cfg.get("model_class_defaults") or {}).items():
        if isinstance(raw, dict):
            try:
                class_defaults[mc] = _lane_from_mapping(raw, source="model_class").to_dict()
            except ValueError:
                class_defaults[mc] = raw
    return {
        "routing_version": cfg.get("routing_version", ROUTING_VERSION),
        "enforce": enforcement_enabled(cfg),
        "loaded_from": cfg.get("_loaded_from"),
        "guild_lanes": guild_lanes,
        "model_class_defaults": class_defaults,
        "wrapper_bin_dirs": cfg.get("wrapper_bin_dirs") or [],
    }


def install_wrapper_scripts(
    target_dir: Path,
    *,
    hermes_binary: str | None = None,
    force: bool = False,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write portable hermes lane wrappers into target_dir for other operators.

    Each wrapper is: exec <hermes> --provider <p> -m <model> \"$@\"
    """
    cfg = config if config is not None else load_routing_config()
    target_dir = target_dir.expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    hermes_bin = hermes_binary or shutil.which("hermes") or "hermes"

    lanes: dict[str, Lane] = {}
    for raw in (cfg.get("model_class_defaults") or {}).values():
        if isinstance(raw, dict) and raw.get("wrapper"):
            lane = _lane_from_mapping(raw, source="model_class")
            lanes[lane.wrapper] = lane
    for raw in (cfg.get("guild_lanes") or {}).values():
        if isinstance(raw, dict) and raw.get("wrapper"):
            lane = _lane_from_mapping(raw, source="guild")
            lanes[lane.wrapper] = lane
            if lane.fallback_wrapper and lane.fallback_wrapper in lanes:
                continue

    installed: list[str] = []
    skipped: list[str] = []
    for wrapper, lane in sorted(lanes.items()):
        path = target_dir / wrapper
        if path.exists() and not force:
            skipped.append(str(path))
            continue
        provider = lane.provider or "zai"
        model = lane.model or "glm-5.2"
        body = (
            "#!/bin/sh\n"
            f"# LPOS model-routing wrapper ({ROUTING_VERSION})\n"
            f"# lane family={lane.family} provider={provider} model={model}\n"
            f'exec {hermes_bin} --provider {provider} -m {model} "$@"\n'
        )
        path.write_text(body, encoding="utf-8")
        path.chmod(0o755)
        installed.append(str(path))

    return {
        "target_dir": str(target_dir),
        "hermes_binary": hermes_bin,
        "installed": installed,
        "skipped": skipped,
        "routing_version": ROUTING_VERSION,
    }


# Back-compat helper used by gates model-separation checks
_FAMILY_RE = re.compile(r"[a-z0-9.+_-]+", re.I)


def families_differ(a: str, b: str) -> bool:
    """True if two model strings are different families."""
    return model_family(a) != model_family(b) and bool(_FAMILY_RE.search(a or "")) and bool(
        _FAMILY_RE.search(b or "")
    )
