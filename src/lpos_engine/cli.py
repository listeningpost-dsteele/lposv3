"""Command-line interface for LPOS v4 installation, operation, and inspection."""

from __future__ import annotations

import argparse
import json
import sys
from importlib.resources import files as resource_files
from pathlib import Path

from . import __version__
from .canonical import canonical_json
from .context import SpecRepository
from .engine import LPOSRuntime, RuntimeConfig
from .evals import catalog as benchmark_catalog
from .evals import run_core_evaluations
from .models import MaterialitySignals, MessageIdentity
from .routing import CapabilityRegistry
from .store import SQLiteStore
from .workflows import catalog as workflow_catalog
from .workflows import load_all as load_all_workflows


def _print(value) -> None:
    print(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False))


def _schema_files(schema_dir: Path | None = None):
    if schema_dir is None:
        root = resource_files("lpos_engine.schemas")
        paths = sorted(
            (item for item in root.iterdir() if item.name.endswith(".schema.json")),
            key=lambda item: item.name,
        )
    else:
        root = schema_dir
        paths = sorted(root.glob("*.schema.json"))
    if not paths:
        raise RuntimeError(f"no schemas found under {root}")
    return root, paths


def _validate_schemas(schema_dir: Path | None = None) -> dict:
    root, paths = _schema_files(schema_dir)
    try:
        from jsonschema.validators import validator_for
    except ImportError:
        for path in paths:
            json.loads(path.read_text(encoding="utf-8"))
        return {
            "root": str(root),
            "schemas": len(paths),
            "status": "JSON parsed; install the dev extra for full JSON Schema validation",
        }
    for path in paths:
        value = json.loads(path.read_text(encoding="utf-8"))
        validator_for(value).check_schema(value)
    return {"root": str(root), "schemas": len(paths), "status": "valid"}


def cmd_version(args: argparse.Namespace) -> int:
    _print({"name": "LPOS", "version": __version__})
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    store = SQLiteStore(args.db)
    _print(
        {
            "os_version": __version__,
            "database": str(store.path),
            "migrations": list(store.list_migrations()),
            "integrity": store.integrity_check(),
            "status": "initialized",
        }
    )
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    db = workspace / "lpos-state.db"
    runtime = LPOSRuntime.local(
        RuntimeConfig(
            database_path=db,
            spec_root=Path(args.spec_root).resolve() if args.spec_root else None,
            verified_identities={"email": (args.principal_email,)},
        ),
        file_action_root=workspace / "files",
    )
    task = runtime.submit_task(
        "Build and verify the integrated LPOS v4 operating-system core.",
        required_capabilities=("software_architecture", "software_implementation", "testing"),
        materiality_signals=MaterialitySignals(modifies_long_lived_specification=True),
    )
    runtime.record_interpretation(
        task.task_id,
        instruction_verbatim=task.principal_instruction,
        interpretation=(
            "Produce a deterministic LPOS v4 artifact while preserving Principal authority, "
            "exact-action approval, transactional state, and isolated review."
        ),
        invariants=(
            "The Principal remains the only source of consequential approval.",
            "No external action executes before a bound verified approval.",
            "The creator context cannot approve its own material artifact.",
        ),
        verification_plan=(
            "Persist the task and event stream transactionally.",
            "Exercise an exact-action approval through a verified identity.",
            "Run a fresh-context independent review before completion.",
        ),
        spec_ref="LPOS-v4:packaged-specification",
    )
    spec = runtime.record_artifact_spec(
        task.task_id,
        structural_decisions={
            "control_plane": "deterministic",
            "intelligence_plane": "adapter boundary",
            "state": "SQLite plus append-only events",
        },
        invariants=("LPOS v4 component identifiers remain stable within the release",),
        approved_by=args.principal_email,
    )
    artifact = runtime.create_artifact(task.task_id, artifact_specification=spec)
    action, request = runtime.plan_action(
        task.task_id,
        kind="external_send",
        parameters={
            "to": args.principal_email,
            "subject": "LPOS v4 local verification completed",
            "artifact_hash": artifact.content_hash,
        },
        external=True,
        reversible=False,
        idempotency_key=f"demo:{task.task_id}:notify",
    )
    assert request is not None
    runtime.grant_action_approval(
        request.question_id,
        message_identity=MessageIdentity(
            channel="email",
            provider="local-demo",
            message_id=f"demo-{task.task_id}",
            thread_id=request.question_id,
            sender=args.principal_email,
        ),
        verified_identity=args.principal_email,
    )
    runtime.apply_action(action.action_id)
    runtime.review_latest_artifact(
        task.task_id,
        intended_outcome="A completed and audited LPOS v4 core run.",
        completion_summary="LPOS v4 local verification completed and passed isolated review.",
    )
    report = runtime.store.get_completion_report(task.task_id)
    export = runtime.store.export_jsonl(workspace / "events.jsonl")
    _print(
        {
            "os_version": __version__,
            "workspace": str(workspace),
            "database": str(db),
            "event_export": str(export),
            "task": task.to_dict(),
            "artifact": artifact.to_dict(),
            "completion_report": report.to_dict() if report else None,
            "external_action_mode": "record-only",
        }
    )
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    store = SQLiteStore(args.db)
    state = store.get_task(args.task_id)
    artifact = store.get_latest_artifact(args.task_id)
    report = store.get_completion_report(args.task_id)
    _print(
        {
            "task": {
                "envelope": state["envelope"].to_dict(),
                "status": state["status"].value,
                "version": state["version"],
                "created_at": state["created_at"],
                "updated_at": state["updated_at"],
            },
            "artifact": artifact.to_dict() if artifact else None,
            "actions": [
                {
                    "plan": item["plan"].to_dict(),
                    "status": item["status"].value,
                    "result": item["result"].to_dict() if item["result"] else None,
                }
                for item in store.list_actions(args.task_id)
            ],
            "completion_report": report.to_dict() if report else None,
            "events": store.list_events(stream_id=args.task_id),
        }
    )
    return 0


def cmd_events(args: argparse.Namespace) -> int:
    store = SQLiteStore(args.db)
    _print(store.list_events(stream_type=args.stream_type, stream_id=args.stream_id))
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    store = SQLiteStore(args.db)
    path = store.export_jsonl(args.output)
    _print({"output": str(path), "events": len(store.list_events())})
    return 0


def cmd_validate_schemas(args: argparse.Namespace) -> int:
    _print(_validate_schemas(args.schema_dir))
    return 0


def cmd_list_specialists(args: argparse.Namespace) -> int:
    registry = CapabilityRegistry.default()
    _print(
        {
            "os_version": __version__,
            "specialists": [
                {
                    "id": item.specialist_id,
                    "name": item.name,
                    "guild": item.guild,
                    "model_class": item.model_class,
                    "capabilities": sorted(item.capabilities),
                    "craft_standards": list(item.craft_standards),
                }
                for item in registry.profiles
            ],
        }
    )
    return 0


def cmd_list_workflows(args: argparse.Namespace) -> int:
    _print({"os_version": __version__, "standing_operations": list(workflow_catalog())})
    return 0


def cmd_list_benchmarks(args: argparse.Namespace) -> int:
    _print({"os_version": __version__, "benchmarks": list(benchmark_catalog())})
    return 0


def cmd_evals(args: argparse.Namespace) -> int:
    result = run_core_evaluations()
    _print(result)
    return 0 if result["failed"] == 0 else 1


def cmd_doctor(args: argparse.Namespace) -> int:
    repository = SpecRepository.packaged()
    kernel_ref, kernel = repository.load_kernel()
    registry = CapabilityRegistry.default()
    workflows = load_all_workflows()
    schema_result = _validate_schemas(args.schema_dir)
    result = {
        "name": "LPOS",
        "version": __version__,
        "status": "healthy",
        "specification": {
            "kernel": kernel_ref,
            "kernel_loaded": bool(kernel),
        },
        "specialists": len(registry.profiles),
        "standing_operations": len(workflows),
        "benchmarks": len(benchmark_catalog()),
        "schemas": schema_result,
        "python": sys.version.split()[0],
    }
    if args.db is not None:
        store = SQLiteStore(args.db)
        result["database"] = {
            "path": str(store.path),
            "integrity": store.integrity_check(),
            "migrations": list(store.list_migrations()),
        }
    if (
        not kernel
        or len(registry.profiles) != 33
        or len(workflows) != 22
        or len(benchmark_catalog()) != 55
    ):
        result["status"] = "unhealthy"
        _print(result)
        return 1
    _print(result)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lpos", description="LPOS v4 operating system")
    sub = parser.add_subparsers(dest="command", required=True)

    version = sub.add_parser("version", help="show the installed LPOS version")
    version.set_defaults(func=cmd_version)

    init = sub.add_parser("init", help="initialize the transactional state database")
    init.add_argument("--db", type=Path, required=True)
    init.set_defaults(func=cmd_init)

    demo = sub.add_parser("demo", help="run the no-side-effect integrated verification flow")
    demo.add_argument("--workspace", type=Path, required=True)
    demo.add_argument("--spec-root", type=Path, help="optional override for the packaged v4 specification")
    demo.add_argument("--principal-email", default="principal@example.com")
    demo.set_defaults(func=cmd_demo)

    inspect = sub.add_parser("inspect", help="inspect a task and its completion state")
    inspect.add_argument("--db", type=Path, required=True)
    inspect.add_argument("--task-id", required=True)
    inspect.set_defaults(func=cmd_inspect)

    events = sub.add_parser("events", help="list immutable audit events")
    events.add_argument("--db", type=Path, required=True)
    events.add_argument("--stream-type")
    events.add_argument("--stream-id")
    events.set_defaults(func=cmd_events)

    export = sub.add_parser("export", help="export the append-only event stream as JSONL")
    export.add_argument("--db", type=Path, required=True)
    export.add_argument("--output", type=Path, required=True)
    export.set_defaults(func=cmd_export)

    validate = sub.add_parser("validate-schemas", help="validate the executable JSON Schemas")
    validate.add_argument("--schema-dir", type=Path, default=None)
    validate.set_defaults(func=cmd_validate_schemas)

    specialists = sub.add_parser("list-specialists", help="show the 33 capability-routable specialists")
    specialists.set_defaults(func=cmd_list_specialists)

    workflows = sub.add_parser("list-workflows", help="show the 22 packaged Standing Operations")
    workflows.set_defaults(func=cmd_list_workflows)

    benchmarks = sub.add_parser("list-benchmarks", help="show the 55 fixed benchmark fixtures")
    benchmarks.set_defaults(func=cmd_list_benchmarks)

    evals = sub.add_parser("evals", help="run deterministic core evaluations against all fixtures")
    evals.set_defaults(func=cmd_evals)

    doctor = sub.add_parser("doctor", help="verify the integrated specification, runtime assets, and database")
    doctor.add_argument("--db", type=Path)
    doctor.add_argument("--schema-dir", type=Path, default=None)
    doctor.set_defaults(func=cmd_doctor)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(canonical_json({"error": type(exc).__name__, "message": str(exc)}), file=sys.stderr)
        return 1
