#!/usr/bin/env python3
"""Build the active 4.7 candidate registry from the accepted expert corpus."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROLE_WORDS = {
    "and",
    "specialist",
    "analyst",
    "engineer",
    "manager",
    "lead",
    "architect",
    "designer",
    "steward",
    "coordinator",
    "director",
    "reviewer",
}

LEGACY_TARGETS = {
    "SPECIALIST-001": "SPECIALIST-STRATEGIC-PLANNER",
    "SPECIALIST-002": "SPECIALIST-DECISION-ANALYST",
    "SPECIALIST-003": "SPECIALIST-EVIDENCE-INTEGRITY-ANALYST",
    "SPECIALIST-004": "SPECIALIST-SCENARIO-AND-STRATEGIC-RISK-ANALYST",
    "SPECIALIST-005": "SPECIALIST-PORTFOLIO-AND-INITIATIVE-STRATEGIST",
    "SPECIALIST-006": "SPECIALIST-RESEARCH-ANALYST",
    "SPECIALIST-007": "SPECIALIST-TECHNOLOGY-INTELLIGENCE-ANALYST",
    "SPECIALIST-008": "SPECIALIST-EVIDENCE-INTEGRITY-ANALYST",
    "SPECIALIST-009": "SPECIALIST-COMPETITIVE-INTELLIGENCE-ANALYST",
    "SPECIALIST-010": "SPECIALIST-MARKET-RESEARCHER",
    "SPECIALIST-011": "SPECIALIST-SOFTWARE-ARCHITECT",
    "SPECIALIST-012": "SPECIALIST-SOFTWARE-ENGINEER",
    "SPECIALIST-013": "SPECIALIST-SOFTWARE-REVIEWER",
    "SPECIALIST-014": "SPECIALIST-CODE-AND-STRUCTURAL-TEST-ENGINEER",
    "SPECIALIST-015": "SPECIALIST-SOFTWARE-MAINTENANCE-AND-DEBUGGING-ENGINEER",
    "SPECIALIST-016": "SPECIALIST-SERVICE-OPERATIONS-ANALYST",
    "SPECIALIST-017": "SPECIALIST-WORKFLOW-AUTOMATION-ENGINEER",
    "SPECIALIST-018": "SPECIALIST-PORTFOLIO-AND-INITIATIVE-STRATEGIST",
    "SPECIALIST-019": "SPECIALIST-EXECUTIVE-COMMUNICATIONS-WRITER",
    "SPECIALIST-020": "SPECIALIST-TECHNICAL-WRITER",
    "SPECIALIST-021": "SPECIALIST-EDITOR",
    "SPECIALIST-022": "SPECIALIST-FINANCIAL-PLANNING-AND-ANALYSIS-ANALYST",
    "SPECIALIST-023": "SPECIALIST-PRICING-AND-PACKAGING-ECONOMIST",
    "SPECIALIST-024": "SPECIALIST-SECURITY-ARCHITECT",
    "SPECIALIST-025": "SPECIALIST-THREAT-MODELING-SPECIALIST",
    "SPECIALIST-026": "SPECIALIST-LEGAL-RESEARCH-ANALYST",
    "SPECIALIST-027": "SPECIALIST-PRODUCT-MANAGER",
    "SPECIALIST-028": "SPECIALIST-UX-RESEARCHER",
    "SPECIALIST-029": "SPECIALIST-RELATIONSHIP-INTELLIGENCE-SPECIALIST",
    "SPECIALIST-030": "SPECIALIST-DATA-ANALYST",
    "SPECIALIST-031": "SPECIALIST-OPERATIONS-SYSTEMS-ARCHITECT",
    "SPECIALIST-032": "SPECIALIST-PRODUCT-DESIGNER",
    "SPECIALIST-033": "SPECIALIST-ADVERSARIAL-ASSURANCE-LEAD",
    "SPECIALIST-034": "SPECIALIST-QUALITY-AND-RELEASE-DIRECTOR",
    "SPECIALIST-035": "SPECIALIST-SOFTWARE-REVIEWER",
    "SPECIALIST-036": "SPECIALIST-ACCEPTANCE-TEST-ARCHITECT",
    "SPECIALIST-037": "SPECIALIST-ACCEPTANCE-TEST-ARCHITECT",
    "SPECIALIST-038": "SPECIALIST-CODE-AND-STRUCTURAL-TEST-ENGINEER",
    "SPECIALIST-039": "SPECIALIST-CODE-AND-STRUCTURAL-TEST-ENGINEER",
    "SPECIALIST-040": "SPECIALIST-SYSTEM-AND-END-TO-END-TEST-ENGINEER",
    "SPECIALIST-041": "SPECIALIST-CODE-AND-STRUCTURAL-TEST-ENGINEER",
    "SPECIALIST-042": "SPECIALIST-CODE-AND-STRUCTURAL-TEST-ENGINEER",
    "SPECIALIST-043": "SPECIALIST-SOFTWARE-REVIEWER",
    "SPECIALIST-044": "SPECIALIST-TEST-RELIABILITY-ENGINEER",
    "SPECIALIST-045": "SPECIALIST-RELEASE-VERIFICATION-AUDITOR",
}


def parse_frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"missing frontmatter: {path}")
    lines = text.split("---", 2)[1].strip().splitlines()
    result: dict[str, Any] = {}
    current: str | None = None
    for line in lines:
        if line and not line.startswith((" ", "-")) and ":" in line:
            current, value = line.split(":", 1)
            current = current.strip()
            result[current] = value.strip()
        elif line.startswith("- ") and current:
            if not isinstance(result.get(current), list):
                result[current] = []
            result[current].append(line[2:].strip())
    return result


def derived_capabilities(entity_id: str, guild_id: str) -> set[str]:
    specialist_slug = entity_id.removeprefix("SPECIALIST-").lower().replace("-", "_")
    guild_slug = guild_id.removeprefix("GUILD-").lower().replace("-", "_")
    words = [word for word in specialist_slug.split("_") if word not in ROLE_WORDS]
    capabilities = {specialist_slug, guild_slug, *words}
    capabilities.update("_".join(words[index : index + 2]) for index in range(len(words) - 1))
    return {capability for capability in capabilities if capability}


def build(root: Path) -> dict[str, Any]:
    config_dir = root / "src" / "lpos_engine" / "config"
    spec_dir = root / "src" / "lpos_engine" / "spec"
    legacy = json.loads((config_dir / "legacy_v46_registry.json").read_text(encoding="utf-8"))
    migrated: dict[str, list[dict[str, Any]]] = {}
    for profile in legacy["specialists"]:
        target = LEGACY_TARGETS[profile["specialist_id"]]
        migrated.setdefault(target, []).append(profile)

    profiles: list[dict[str, Any]] = []
    for path in sorted((spec_dir / "specialists").glob("SPECIALIST-*.md")):
        metadata = parse_frontmatter(path)
        specialist_id = str(metadata["id"])
        guild_id = str(metadata["guild"])
        aliases = migrated.get(specialist_id, [])
        capabilities = derived_capabilities(specialist_id, guild_id)
        for alias in aliases:
            capabilities.update(alias["capabilities"])
        model_class = min(aliases, key=lambda item: item["priority"])["model_class"] if aliases else "executive"
        priority = min((int(item["priority"]) for item in aliases), default=100)
        standards = metadata.get("craft_standards", [])
        if not isinstance(standards, list):
            standards = []
        profiles.append(
            {
                "specialist_id": specialist_id,
                "name": metadata["title"],
                "guild": guild_id,
                "capabilities": sorted(capabilities),
                "craft_standards": standards,
                "model_class": model_class,
                "priority": priority,
                "charter_path": f"specialists/{path.name}",
                "guild_charter_path": f"guilds/{guild_id}.md",
                "runtime_lifecycle": "active_candidate",
            }
        )

    if len(profiles) != 103:
        raise ValueError(f"expected 103 specialists, found {len(profiles)}")
    return {
        "schema_version": 4,
        "os_version": "4.8.0",
        "registry_version": "4.8.0",
        "activation_status": "active",
        "source_catalog": "default_registry.json",
        "specialists": profiles,
    }


def migrate_active_references(root: Path, registry: dict[str, Any]) -> None:
    profiles = {item["specialist_id"]: item for item in registry["specialists"]}
    evals_dir = root / "src" / "lpos_engine" / "evals"
    for path in sorted(evals_dir.glob("BENCH-S*.json")):
        fixture = json.loads(path.read_text(encoding="utf-8"))
        legacy_id = f"SPECIALIST-{path.stem.removeprefix('BENCH-S')}"
        target_id = LEGACY_TARGETS[legacy_id]
        profile = profiles[target_id]
        fixture["component_id"] = target_id
        fixture["expected"].update(
            {
                "craft_standards": profile["craft_standards"],
                "lead_guild": profile["guild"],
                "lead_specialist": target_id,
                "model_class": fixture["inputs"].get(
                    "preferred_model_class", profile["model_class"]
                ),
            }
        )
        fixture["success_criteria"] = [
            item.replace(legacy_id, target_id) for item in fixture["success_criteria"]
        ]
        path.write_text(json.dumps(fixture, indent=2) + "\n", encoding="utf-8")

    catalog_path = evals_dir / "catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    for item in catalog["benchmarks"]:
        component_id = item["component_id"]
        if component_id in LEGACY_TARGETS:
            item["component_id"] = LEGACY_TARGETS[component_id]
    catalog_path.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")

    active_reference_files = (
        root / "src" / "lpos_engine" / "spec" / "STANDING-OPERATIONS.md",
        root / "src" / "lpos_engine" / "schemas" / "security-assessment.schema.json",
        root / "schemas" / "security-assessment.schema.json",
    )
    for path in active_reference_files:
        text = path.read_text(encoding="utf-8")
        for legacy_id, target_id in LEGACY_TARGETS.items():
            text = text.replace(legacy_id, target_id)
        path.write_text(text, encoding="utf-8")


def activate_candidate_catalog(root: Path) -> None:
    path = root / "src" / "lpos_engine" / "config" / "candidate_catalog.json"
    catalog = json.loads(path.read_text(encoding="utf-8"))
    lifecycle = {
        "guild": (False, "active_governance"),
        "specialist": (True, "active_candidate"),
        "craft-standard": (False, "active_standard"),
    }
    for entity in catalog["entities"]:
        entity["routable"], entity["runtime_lifecycle"] = lifecycle[entity["entity_type"]]
    path.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    registry = build(args.root.resolve())
    rendered = json.dumps(registry, indent=2, sort_keys=False) + "\n"
    packaged = args.root / "src" / "lpos_engine" / "config" / "default_registry.json"
    mirror = args.root / "config" / "default_registry.json"
    packaged.write_text(rendered, encoding="utf-8")
    mirror.write_text(rendered, encoding="utf-8")
    migrate_active_references(args.root.resolve(), registry)
    activate_candidate_catalog(args.root.resolve())
    print(f"built active candidate registry with {len(registry['specialists'])} specialists")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
