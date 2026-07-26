"""Tolerant loader for a repository testing manifest.

The manifest names the repository-native build, test, lint, and type-check commands. The
standard is explicit that the system must never invent these commands: they come only
from the manifest. This loader therefore reads a manifest and surfaces exactly the
commands it declares, and no others.

To avoid adding a third-party dependency, the loader accepts a JSON manifest directly
and, failing that, parses a small, well-defined subset of YAML (nested mappings, scalar
values, and lists of scalars or of single-line mappings) with the standard library only.
It never raises on malformed input; an unparseable or missing manifest yields no
commands.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

_COMMAND_KEYS = (
    "format_check",
    "lint",
    "type_check",
    "build",
    "unit",
    "acceptance",
    "integration",
    "property",
    "mutation",
    "architecture",
    "security",
    "performance",
    "smoke",
)


def _coerce_scalar(text: str) -> Any:
    raw = text.strip()
    if (raw.startswith('"') and raw.endswith('"')) or (
        raw.startswith("'") and raw.endswith("'")
    ):
        return raw[1:-1]
    lowered = raw.lower()
    if lowered in {"true", "yes"}:
        return True
    if lowered in {"false", "no"}:
        return False
    if lowered in {"null", "~", ""}:
        return "" if raw == "" else None
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        if not inner:
            return []
        return [_coerce_scalar(part) for part in inner.split(",")]
    return raw


def _tokenize(text: str) -> list[tuple[int, str]]:
    tokens: list[tuple[int, str]] = []
    for raw_line in text.splitlines():
        line = raw_line.split(" #", 1)[0].rstrip() if " #" in raw_line else raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        tokens.append((indent, stripped))
    return tokens


def _parse_block(tokens: list[tuple[int, str]], start: int, indent: int) -> tuple[Any, int]:
    """Recursively parse tokens at a given indent into a dict or list.

    Returns the parsed container and the index of the first unconsumed token.
    """
    if start >= len(tokens):
        return {}, start
    # The block's own indent is the indent of its first token; this makes the parser
    # robust to any consistent indentation width (2 spaces, 4 spaces, ...).
    indent = tokens[start][0]
    is_list = tokens[start][1].startswith("- ")
    container: Any = [] if is_list else {}
    index = start
    while index < len(tokens):
        cur_indent, content = tokens[index]
        if cur_indent < indent:
            break
        if cur_indent > indent:
            # Should have been consumed by a nested call; skip defensively.
            index += 1
            continue
        if content.startswith("- "):
            if not isinstance(container, list):
                break
            item = content[2:].strip()
            if ":" in item and not item.startswith(("'", '"')):
                key, _, value = item.partition(":")
                mapping: dict[str, Any] = {}
                value = value.strip()
                if value:
                    mapping[key.strip()] = _coerce_scalar(value)
                    index += 1
                else:
                    child, index = _parse_block(tokens, index + 1, indent + 1)
                    mapping[key.strip()] = child
                # Absorb continuation "key: value" lines that belong to this item.
                while index < len(tokens) and tokens[index][0] > indent and not tokens[index][1].startswith("- "):
                    c_indent, c_content = tokens[index]
                    if ":" in c_content:
                        c_key, _, c_value = c_content.partition(":")
                        c_value = c_value.strip()
                        if c_value:
                            mapping[c_key.strip()] = _coerce_scalar(c_value)
                            index += 1
                        else:
                            nested, index = _parse_block(tokens, index + 1, c_indent + 1)
                            mapping[c_key.strip()] = nested
                    else:
                        index += 1
                container.append(mapping)
            else:
                container.append(_coerce_scalar(item))
                index += 1
            continue
        if ":" in content:
            if not isinstance(container, dict):
                break
            key, _, value = content.partition(":")
            key = key.strip()
            value = value.strip()
            if value:
                container[key] = _coerce_scalar(value)
                index += 1
            else:
                child, index = _parse_block(tokens, index + 1, indent + 1)
                container[key] = child
            continue
        # Unrecognized line; skip.
        index += 1
    return container, index


def _parse_yaml_subset(text: str) -> dict[str, Any]:
    """Parse a minimal YAML subset into nested dict/list structures.

    Supports comments, ``key: value`` scalars, ``key:`` nested blocks, ``- value``
    list items, and ``- key: value`` list-of-mapping items with continuation lines.
    Anything it cannot understand is skipped rather than raised.
    """
    tokens = _tokenize(text)
    if not tokens:
        return {}
    base_indent = tokens[0][0]
    parsed, _ = _parse_block(tokens, 0, base_indent)
    return parsed if isinstance(parsed, dict) else {}


def parse_manifest(text: str) -> dict[str, Any]:
    """Parse manifest text (JSON first, then the YAML subset). Never raises."""
    if not text or not text.strip():
        return {}
    try:
        value = json.loads(text)
        if isinstance(value, dict):
            return value
    except (ValueError, TypeError):
        pass
    try:
        parsed = _parse_yaml_subset(text)
    except Exception:  # pragma: no cover - the parser is defensive
        return {}
    return parsed if isinstance(parsed, dict) else {}


def load_manifest(source: str | os.PathLike[str] | None) -> dict[str, Any]:
    """Load a manifest from a path (or raw text). A missing manifest yields ``{}``."""
    if source is None:
        return {}
    text: str
    try:
        path = Path(source)
        if path.exists() and path.is_file():
            text = path.read_text(encoding="utf-8")
        else:
            # Treat the string as inline manifest text only if it looks like content.
            source_str = str(source)
            text = source_str if ("\n" in source_str or ":" in source_str or source_str.strip().startswith("{")) else ""
    except (OSError, ValueError):
        return {}
    return parse_manifest(text)


def manifest_commands(manifest: Mapping[str, Any] | None) -> dict[str, str]:
    """Return only the non-empty commands the manifest declares.

    Commands are never invented: a command absent or empty in the manifest is simply
    not returned.
    """
    if not isinstance(manifest, Mapping):
        return {}
    commands = manifest.get("commands")
    if not isinstance(commands, Mapping):
        return {}
    result: dict[str, str] = {}
    for key in _COMMAND_KEYS:
        value = commands.get(key)
        if isinstance(value, str) and value.strip():
            result[key] = value.strip()
    # Also surface any additional declared, non-empty string commands.
    for key, value in commands.items():
        if key not in result and isinstance(value, str) and value.strip():
            result[key] = value.strip()
    return result


def load_commands(source: str | os.PathLike[str] | None) -> dict[str, str]:
    """Convenience: load a manifest and return only its declared commands."""
    return manifest_commands(load_manifest(source))


__all__ = [
    "parse_manifest",
    "load_manifest",
    "manifest_commands",
    "load_commands",
]
