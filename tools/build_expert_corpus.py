#!/usr/bin/env python3
"""Build the LPOS 4.7 candidate source tree from the approved v1.2 corpus.

This generator copies professional source text without rewriting it. Runtime
activation is intentionally kept outside the candidate files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

EXPECTED_SOURCE_SHA256 = "fcc787db6f8ab0be691f9030af927005a005561db1c0fecdee5f6dbdc87a060f"
EXPECTED_COUNTS = {"guild": 20, "specialist": 103, "craft-standard": 122}
MANIFEST_ROW = re.compile(
    r"^\|\s*(guild|specialist|craft-standard)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|$"
)
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
ID_LINE = re.compile(r"^\s*id:\s*([^\s#]+)\s*$")


@dataclass(frozen=True)
class Entity:
    entity_type: str
    entity_id: str
    title: str
    relative_path: str


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def heading_at(lines: list[str], index: int) -> tuple[int, str] | None:
    match = HEADING.match(lines[index])
    if not match:
        return None
    return len(match.group(1)), match.group(2).strip()


def parse_manifest(lines: list[str]) -> list[Entity]:
    start = next(i for i, line in enumerate(lines) if line.strip().lower() == "# entity file manifest")
    end = next(i for i in range(start + 1, len(lines)) if lines[i].startswith("# Legacy "))
    entities: list[Entity] = []
    for line in lines[start:end]:
        match = MANIFEST_ROW.match(line)
        if not match:
            continue
        entity_type, entity_id, title, relative_path = (part.strip() for part in match.groups())
        entities.append(Entity(entity_type, entity_id, title, relative_path))

    actual_counts = {
        entity_type: sum(entity.entity_type == entity_type for entity in entities)
        for entity_type in EXPECTED_COUNTS
    }
    if actual_counts != EXPECTED_COUNTS:
        raise RuntimeError(f"entity manifest count mismatch: {actual_counts}")
    ids = [entity.entity_id for entity in entities]
    paths = [entity.relative_path for entity in entities]
    if len(ids) != len(set(ids)):
        raise RuntimeError("entity manifest contains duplicate IDs")
    if len(paths) != len(set(paths)):
        raise RuntimeError("entity manifest contains duplicate paths")
    return entities


def find_yaml_block(lines: list[str], entity_id: str, corpus_start: int) -> tuple[int, int, int]:
    matches = [
        i
        for i in range(corpus_start, len(lines))
        if (match := ID_LINE.match(lines[i])) and match.group(1) == entity_id
    ]
    if len(matches) != 1:
        raise RuntimeError(f"expected one corpus ID line for {entity_id}, found {len(matches)}")
    id_index = matches[0]
    fence_start = next(
        (i for i in range(id_index - 1, max(corpus_start - 1, id_index - 40), -1) if lines[i].strip() == "```yaml"),
        None,
    )
    if fence_start is None:
        raise RuntimeError(f"missing YAML fence before {entity_id}")
    fence_end = next(
        (i for i in range(id_index + 1, min(len(lines), id_index + 80)) if lines[i].strip() == "```"),
        None,
    )
    if fence_end is None:
        raise RuntimeError(f"missing YAML fence end after {entity_id}")
    return fence_start, id_index, fence_end


def extract_entity(lines: list[str], entity: Entity, corpus_start: int) -> tuple[str, int, int]:
    fence_start, _, fence_end = find_yaml_block(lines, entity.entity_id, corpus_start)
    metadata_heading = next(
        (i for i in range(fence_start - 1, corpus_start - 1, -1) if heading_at(lines, i)),
        None,
    )
    if metadata_heading is None:
        raise RuntimeError(f"missing entity heading for {entity.entity_id}")
    metadata_level, _ = heading_at(lines, metadata_heading) or (0, "")

    next_heading = next(
        (i for i in range(fence_end + 1, len(lines)) if heading_at(lines, i)),
        None,
    )
    body_heading = None
    if next_heading is not None:
        next_level, next_title = heading_at(lines, next_heading) or (7, "")
        title_key = normalized(entity.title.replace(" Guild Charter", ""))
        next_key = normalized(next_title.replace(" Guild Charter", ""))
        if next_level <= metadata_level and (title_key == next_key or title_key in next_key or next_key in title_key):
            body_heading = next_heading

    boundary_from = body_heading if body_heading is not None else fence_end
    boundary_level = (heading_at(lines, body_heading) or (metadata_level, ""))[0] if body_heading is not None else metadata_level
    end = len(lines)
    for i in range(boundary_from + 1, len(lines)):
        parsed = heading_at(lines, i)
        if parsed and parsed[0] <= boundary_level:
            end = i
            break

    yaml_payload = lines[fence_start + 1 : fence_end]
    body = lines[fence_end + 1 : end]
    while body and (not body[0].strip() or body[0].strip() == "---"):
        body.pop(0)
    while body and (not body[-1].strip() or body[-1].strip() == "---"):
        body.pop()
    extracted_ids = {
        match.group(1)
        for line in yaml_payload
        if (match := ID_LINE.match(line)) is not None
    }
    if entity.entity_id not in extracted_ids:
        raise RuntimeError(f"extracted source lost ID {entity.entity_id}")
    provenance = (
        f"<!-- Generated from LPOS expert corpus v1.2, source SHA-256 {EXPECTED_SOURCE_SHA256}, "
        f"source lines {metadata_heading + 1}-{end}. Runtime lifecycle is governed separately. -->"
    )
    content = "---\n" + "\n".join(yaml_payload) + "\n---\n\n" + provenance
    if body:
        content += "\n\n" + "\n".join(body)
    return content.rstrip() + "\n", metadata_heading + 1, end


def build(source: Path, spec_root: Path, config_root: Path) -> dict[str, object]:
    source_bytes = source.read_bytes()
    actual_source_hash = sha256_bytes(source_bytes)
    if actual_source_hash != EXPECTED_SOURCE_SHA256:
        raise RuntimeError(
            f"source SHA-256 mismatch: expected {EXPECTED_SOURCE_SHA256}, got {actual_source_hash}"
        )
    lines = source_bytes.decode("utf-8").splitlines()
    entities = parse_manifest(lines)
    corpus_start = next(
        i for i, line in enumerate(lines) if line.strip() == "# Accepted Guild Packages and Complete Candidate Role Sources"
    )

    catalog: list[dict[str, object]] = []
    for entity in entities:
        content, source_line_start, source_line_end = extract_entity(lines, entity, corpus_start)
        relative = Path(entity.relative_path)
        destination = spec_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
        catalog.append(
            {
                "entity_type": entity.entity_type,
                "entity_id": entity.entity_id,
                "title": entity.title,
                "source_status": "accepted_candidate",
                "runtime_lifecycle": "candidate",
                "routable": False,
                "path": relative.as_posix(),
                "content_sha256": sha256_bytes(content.encode("utf-8")),
                "source_line_start": source_line_start,
                "source_line_end": source_line_end,
            }
        )

    config_root.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "os_version": "4.7.0-candidate",
        "source": {
            "name": source.name,
            "sha256": actual_source_hash,
        },
        "counts": EXPECTED_COUNTS,
        "entities": catalog,
    }
    catalog_path = config_root / "candidate_catalog.json"
    catalog_text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    catalog_path.write_text(catalog_text, encoding="utf-8")

    index_lines = [
        "# LPOS 4.7 Candidate Expert Corpus",
        "",
        f"Source SHA-256: `{actual_source_hash}`",
        "",
        "Candidate source approval does not grant runtime activation.",
        "",
    ]
    for entity_type in ("guild", "specialist", "craft-standard"):
        index_lines.extend(
            [
                f"## {entity_type.replace('-', ' ').title()}s",
                "",
                *[
                    f"- `{item['entity_id']}`: {item['title']} (`{item['path']}`)"
                    for item in catalog
                    if item["entity_type"] == entity_type
                ],
                "",
            ]
        )
    (spec_root / "EXPERT-CORPUS-INDEX.md").write_text("\n".join(index_lines), encoding="utf-8")

    return {
        "source_sha256": actual_source_hash,
        "catalog_sha256": sha256_bytes(catalog_text.encode("utf-8")),
        "counts": EXPECTED_COUNTS,
        "entities": len(catalog),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--spec-root", type=Path, required=True)
    parser.add_argument("--config-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.source, args.spec_root, args.config_root), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    main()
