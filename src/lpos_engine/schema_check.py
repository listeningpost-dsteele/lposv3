"""Self-contained structural meta-validator for the packaged JSON Schemas.

LPOS-12: a clean offline install has no ``jsonschema`` dependency, and the
previous installer gate silently downgraded "schema validation" to plain
``json.loads``.  This module is a stdlib-only structural validator for the
JSON Schema draft 2020-12 subset actually used by the 20 packaged schemas,
so the gate is ALWAYS meaningful, online or offline.

It is deliberately NOT a full draft 2020-12 implementation.  It verifies
that each document is structurally a schema: every recognized keyword has a
value of the correct shape (``"type"`` names are valid, ``required`` is a
list of strings, ``properties`` maps names to schemas, ``pattern`` compiles,
numeric bounds are numbers, ``enum`` is a non-empty list, in-file ``$ref``
pointers resolve, no duplicate object keys, ...).  A syntactically valid
JSON file that is meta-invalid as a schema (e.g. ``"type": "strnig"``,
``"required": "name"``, ``properties`` as a list, a dangling ``$ref``)
FAILS this check.

Public API
----------
``check_schema(document) -> list[str]``
    Structural problems found in one parsed schema document (empty = pass).

``check_schema_files(paths) -> dict[str, list[str]]``
    Map of file name -> problems for each ``*.schema.json`` path, including
    JSON syntax errors and duplicate-key detection (``object_pairs_hook``).

``validate_for_cli(schema_dir=None) -> dict``
    The always-on installer/CLI gate.  Intended wiring in ``cli.py``::

        from . import schema_check

        def _validate_schemas(schema_dir=None):
            return schema_check.validate_for_cli(schema_dir)

    Behavior:

    - ALWAYS runs the structural checker over every packaged schema
      (``lpos_engine.schemas`` when ``schema_dir`` is None, mirroring the
      existing ``cli._schema_files`` resolution, otherwise
      ``schema_dir/*.schema.json``).
    - ADDITIONALLY runs full ``jsonschema`` meta-validation when that
      optional dependency is importable.
    - RETURNS the exact result-dict shape ``cli.py`` already prints::

          {"root": "<dir>", "schemas": <count>, "status": "valid (structural)"}
          {"root": "<dir>", "schemas": <count>,
           "status": "valid (structural+jsonschema)"}

    - RAISES :class:`SchemaCheckError` (listing every file and problem) on
      any failure, so ``lpos validate-schemas``, ``lpos doctor``, and the
      installer gate fail instead of downgrading to "JSON parsed".
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Sequence
from pathlib import Path

__all__ = [
    "SchemaCheckError",
    "check_schema",
    "check_schema_files",
    "validate_for_cli",
]


class SchemaCheckError(ValueError):
    """One or more schema documents failed structural (or meta) validation."""


_VALID_TYPES = frozenset(
    {"array", "boolean", "integer", "null", "number", "object", "string"}
)

# Keywords whose value must be a single subschema.
_SUBSCHEMA_KEYWORDS = (
    "items",
    "contains",
    "if",
    "then",
    "else",
    "not",
    "propertyNames",
    "unevaluatedItems",
    "unevaluatedProperties",
)
# Keywords whose value must be a non-empty array of subschemas.
_SUBSCHEMA_LIST_KEYWORDS = ("allOf", "anyOf", "oneOf", "prefixItems")
# Keywords whose value must be an object mapping names to subschemas.
_SUBSCHEMA_MAP_KEYWORDS = ("properties", "$defs", "definitions", "dependentSchemas")
# Keywords whose value must be a non-negative integer.
_NON_NEGATIVE_INT_KEYWORDS = (
    "minLength",
    "maxLength",
    "minItems",
    "maxItems",
    "minProperties",
    "maxProperties",
    "minContains",
    "maxContains",
)
# Keywords whose value must be a number (int or float, not bool).
_NUMBER_KEYWORDS = (
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "multipleOf",
)
# Keywords whose value must be a string.
_STRING_KEYWORDS = (
    "$schema",
    "$id",
    "$anchor",
    "$comment",
    "title",
    "description",
    "format",
    "contentEncoding",
    "contentMediaType",
)
# Keywords whose value must be a boolean.
_BOOL_KEYWORDS = ("uniqueItems", "deprecated", "readOnly", "writeOnly")


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _check_type_keyword(value, path: str, problems: list[str]) -> None:
    def _one(name, where: str) -> None:
        if not isinstance(name, str):
            problems.append(f"{where}: type entries must be strings, got {type(name).__name__}")
        elif name not in _VALID_TYPES:
            problems.append(
                f"{where}: {name!r} is not a valid JSON Schema type name "
                f"(valid: {', '.join(sorted(_VALID_TYPES))})"
            )

    if isinstance(value, str):
        _one(value, f"{path}/type")
    elif isinstance(value, list):
        if not value:
            problems.append(f"{path}/type: type array must not be empty")
        seen: set[str] = set()
        for index, item in enumerate(value):
            _one(item, f"{path}/type/{index}")
            if isinstance(item, str):
                if item in seen:
                    problems.append(f"{path}/type: duplicate type name {item!r}")
                seen.add(item)
    else:
        problems.append(
            f"{path}/type: must be a type name string or a list of type names, "
            f"got {type(value).__name__}"
        )


def _walk(node, path: str, problems: list[str], refs: list[tuple[str, str]]) -> None:
    """Validate one schema position (draft 2020-12 allows boolean schemas)."""
    if isinstance(node, bool):
        return
    if not isinstance(node, dict):
        problems.append(
            f"{path}: a schema must be an object or a boolean, got {type(node).__name__}"
        )
        return

    if "type" in node:
        _check_type_keyword(node["type"], path, problems)

    if "enum" in node:
        value = node["enum"]
        if not isinstance(value, list):
            problems.append(f"{path}/enum: must be a list, got {type(value).__name__}")
        elif not value:
            problems.append(f"{path}/enum: must be a non-empty list")

    if "required" in node:
        value = node["required"]
        if not isinstance(value, list):
            problems.append(
                f"{path}/required: must be a list of property names, got {type(value).__name__}"
            )
        else:
            seen: set[str] = set()
            for index, item in enumerate(value):
                if not isinstance(item, str):
                    problems.append(
                        f"{path}/required/{index}: property names must be strings, "
                        f"got {type(item).__name__}"
                    )
                elif item in seen:
                    problems.append(f"{path}/required: duplicate property name {item!r}")
                else:
                    seen.add(item)

    if "pattern" in node:
        value = node["pattern"]
        if not isinstance(value, str):
            problems.append(f"{path}/pattern: must be a string, got {type(value).__name__}")
        else:
            try:
                re.compile(value)
            except re.error as exc:
                problems.append(f"{path}/pattern: invalid regular expression: {exc}")

    if "patternProperties" in node:
        value = node["patternProperties"]
        if not isinstance(value, dict):
            problems.append(
                f"{path}/patternProperties: must be an object mapping patterns to schemas, "
                f"got {type(value).__name__}"
            )
        else:
            for key, sub in value.items():
                try:
                    re.compile(key)
                except re.error as exc:
                    problems.append(
                        f"{path}/patternProperties: invalid regular expression {key!r}: {exc}"
                    )
                _walk(sub, f"{path}/patternProperties/{key}", problems, refs)

    if "$ref" in node:
        value = node["$ref"]
        if not isinstance(value, str) or not value:
            problems.append(
                f"{path}/$ref: must be a non-empty string, got {type(value).__name__}"
            )
        else:
            refs.append((path, value))

    if "additionalProperties" in node:
        value = node["additionalProperties"]
        if not isinstance(value, (bool, dict)):
            problems.append(
                f"{path}/additionalProperties: must be a boolean or a schema, "
                f"got {type(value).__name__}"
            )
        elif isinstance(value, dict):
            _walk(value, f"{path}/additionalProperties", problems, refs)

    for keyword in _SUBSCHEMA_KEYWORDS:
        if keyword not in node:
            continue
        value = node[keyword]
        if keyword == "items" and isinstance(value, list):
            problems.append(
                f"{path}/items: must be a single schema in draft 2020-12 "
                "(use prefixItems for positional schemas)"
            )
            continue
        _walk(value, f"{path}/{keyword}", problems, refs)

    for keyword in _SUBSCHEMA_LIST_KEYWORDS:
        if keyword not in node:
            continue
        value = node[keyword]
        if not isinstance(value, list):
            problems.append(
                f"{path}/{keyword}: must be a list of schemas, got {type(value).__name__}"
            )
        elif not value:
            problems.append(f"{path}/{keyword}: must be a non-empty list of schemas")
        else:
            for index, sub in enumerate(value):
                _walk(sub, f"{path}/{keyword}/{index}", problems, refs)

    for keyword in _SUBSCHEMA_MAP_KEYWORDS:
        if keyword not in node:
            continue
        value = node[keyword]
        if not isinstance(value, dict):
            problems.append(
                f"{path}/{keyword}: must be an object mapping names to schemas, "
                f"got {type(value).__name__}"
            )
        else:
            for key, sub in value.items():
                _walk(sub, f"{path}/{keyword}/{key}", problems, refs)

    for keyword in _NON_NEGATIVE_INT_KEYWORDS:
        if keyword not in node:
            continue
        value = node[keyword]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            problems.append(
                f"{path}/{keyword}: must be a non-negative integer, got {value!r}"
            )

    for keyword in _NUMBER_KEYWORDS:
        if keyword not in node:
            continue
        value = node[keyword]
        if not _is_number(value):
            problems.append(f"{path}/{keyword}: must be a number, got {value!r}")
        elif keyword == "multipleOf" and value <= 0:
            problems.append(f"{path}/multipleOf: must be greater than zero, got {value!r}")

    for keyword in _STRING_KEYWORDS:
        if keyword not in node:
            continue
        value = node[keyword]
        if not isinstance(value, str):
            problems.append(
                f"{path}/{keyword}: must be a string, got {type(value).__name__}"
            )

    for keyword in _BOOL_KEYWORDS:
        if keyword not in node:
            continue
        value = node[keyword]
        if not isinstance(value, bool):
            problems.append(
                f"{path}/{keyword}: must be a boolean, got {type(value).__name__}"
            )

    if "const" in node:
        # Any JSON value is a legal const; nothing to check structurally.
        pass


def _pointer_resolves(document, pointer: str) -> bool:
    node = document
    if pointer == "":
        return True
    if not pointer.startswith("/"):
        return False
    for raw_token in pointer[1:].split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(node, dict):
            if token not in node:
                return False
            node = node[token]
        elif isinstance(node, list):
            if not token.isdigit() or int(token) >= len(node):
                return False
            node = node[int(token)]
        else:
            return False
    return True


def _check_refs(document, refs: Iterable[tuple[str, str]], problems: list[str]) -> None:
    for path, ref in refs:
        if ref == "#":
            continue
        if ref.startswith("#/"):
            if not _pointer_resolves(document, ref[1:]):
                problems.append(
                    f"{path}/$ref: dangling reference {ref!r} does not resolve "
                    "inside this document"
                )
        elif ref.startswith("#"):
            problems.append(
                f"{path}/$ref: anchor reference {ref!r} is not supported by the "
                "offline structural validator; use a #/... JSON pointer"
            )
        else:
            problems.append(
                f"{path}/$ref: external reference {ref!r} cannot be verified by the "
                "offline structural validator; packaged schemas must be self-contained"
            )


def check_schema(document) -> list[str]:
    """Return structural problems for one parsed schema document.

    An empty list means the document is structurally a valid schema within
    the supported draft 2020-12 subset.  Duplicate-key detection requires
    the original text; use :func:`check_schema_files` for files.
    """
    problems: list[str] = []
    refs: list[tuple[str, str]] = []
    _walk(document, "#", problems, refs)
    if isinstance(document, (dict, list)):
        _check_refs(document, refs, problems)
    return problems


def _loads_with_duplicate_detection(text: str) -> tuple[object, list[str]]:
    problems: list[str] = []

    def _hook(pairs):
        obj: dict = {}
        for key, value in pairs:
            if key in obj:
                problems.append(f"duplicate object key {key!r}")
            obj[key] = value
        return obj

    document = json.loads(text, object_pairs_hook=_hook)
    return document, problems


def _check_source(name: str, text: str) -> tuple[object | None, list[str]]:
    try:
        document, problems = _loads_with_duplicate_detection(text)
    except json.JSONDecodeError as exc:
        return None, [f"invalid JSON: {exc}"]
    problems.extend(check_schema(document))
    return document, problems


def check_schema_files(paths: Iterable[str | Path]) -> dict[str, list[str]]:
    """Validate schema files; returns {file name: [problems]} (empty = pass)."""
    results: dict[str, list[str]] = {}
    for raw_path in paths:
        path = Path(raw_path)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            results[path.name] = [f"unreadable: {exc}"]
            continue
        _document, problems = _check_source(path.name, text)
        results[path.name] = problems
    return results


def _schema_sources(schema_dir: str | Path | None) -> tuple[str, list[tuple[str, str]]]:
    """Resolve (root, [(name, text)]) exactly like cli._schema_files does."""
    if schema_dir is None:
        from importlib.resources import files as resource_files

        root = resource_files("lpos_engine.schemas")
        items = sorted(
            (item for item in root.iterdir() if item.name.endswith(".schema.json")),
            key=lambda item: item.name,
        )
        sources = [(item.name, item.read_text(encoding="utf-8")) for item in items]
        root_label = str(root)
    else:
        root = Path(schema_dir)
        items = sorted(root.glob("*.schema.json"))
        sources = [(item.name, item.read_text(encoding="utf-8")) for item in items]
        root_label = str(root)
    if not sources:
        raise SchemaCheckError(f"no schemas found under {root_label}")
    return root_label, sources


def _raise_problems(stage: str, problems_by_name: dict[str, Sequence[str]]) -> None:
    lines = [f"schema validation failed ({stage}):"]
    for name in sorted(problems_by_name):
        for problem in problems_by_name[name]:
            lines.append(f"  {name}: {problem}")
    raise SchemaCheckError("\n".join(lines))


def validate_for_cli(schema_dir: str | Path | None = None) -> dict:
    """Always-on schema gate for cli.py / doctor / the installer.

    Returns ``{"root": str, "schemas": int, "status": str}`` with status
    ``"valid (structural)"`` or ``"valid (structural+jsonschema)"``.
    Raises :class:`SchemaCheckError` on any structural or (when jsonschema
    is available) meta-schema problem, so the install gate fails instead of
    silently downgrading to JSON parsing.
    """
    root_label, sources = _schema_sources(schema_dir)

    documents: dict[str, object] = {}
    failures: dict[str, list[str]] = {}
    for name, text in sources:
        document, problems = _check_source(name, text)
        if problems:
            failures[name] = problems
        else:
            documents[name] = document
    if failures:
        _raise_problems("structural", failures)

    status = "valid (structural)"
    try:
        from jsonschema.validators import validator_for
    except ImportError:
        pass
    else:
        meta_failures: dict[str, list[str]] = {}
        for name, document in documents.items():
            try:
                validator_for(document).check_schema(document)
            except Exception as exc:  # jsonschema.SchemaError and friends
                meta_failures[name] = [str(exc)]
        if meta_failures:
            _raise_problems("jsonschema", meta_failures)
        status = "valid (structural+jsonschema)"

    return {"root": root_label, "schemas": len(sources), "status": status}
