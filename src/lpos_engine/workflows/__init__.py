"""Load the 21 packaged LPOS v4 Standing Operation workflows."""

from __future__ import annotations

import json
from importlib.resources import files

from ..errors import ValidationError
from ..models import WorkflowDefinition


def catalog() -> tuple[dict, ...]:
    try:
        value = json.loads(files(__package__).joinpath("catalog.json").read_text(encoding="utf-8"))
        operations = value["operations"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ValidationError("packaged Standing Operation catalog is missing or invalid") from exc
    if not isinstance(operations, list):
        raise ValidationError("Standing Operation catalog operations must be a list")
    return tuple(dict(item) for item in operations)


def load(so_id: str) -> WorkflowDefinition:
    names = {item["so_id"]: item["workflow"] for item in catalog()}
    try:
        filename = names[so_id]
    except KeyError as exc:
        raise ValidationError(f"unknown Standing Operation: {so_id}") from exc
    try:
        value = json.loads(files(__package__).joinpath(filename).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValidationError(f"workflow {so_id} is missing or invalid") from exc
    return WorkflowDefinition.from_dict(value)


def load_all() -> tuple[WorkflowDefinition, ...]:
    return tuple(load(item["so_id"]) for item in catalog())
