"""A skill as a bounded, ordered set of active rules, plus edit operations."""
from __future__ import annotations

from dataclasses import dataclass, field, replace

from .scorer import ALL_RULES


@dataclass(frozen=True)
class Skill:
    name: str
    rules: tuple[str, ...] = field(default_factory=tuple)

    def with_rules(self, rules) -> "Skill":
        ordered = tuple(dict.fromkeys(rules))
        for rule in ordered:
            if rule not in ALL_RULES:
                raise ValueError(f"unknown rule: {rule}")
        return replace(self, rules=ordered)

    def render(self) -> str:
        lines = [f"# {self.name}", "", "Active CS-001 checks:", ""]
        lines += [f"- {rule}" for rule in self.rules] or ["- (none)"]
        return "\n".join(lines) + "\n"


@dataclass(frozen=True)
class Edit:
    op: str
    rule: str
    rationale: str

    def apply(self, skill: Skill) -> Skill:
        current = list(skill.rules)
        if self.op == "add":
            if self.rule not in current:
                current.append(self.rule)
        elif self.op == "remove":
            current = [rule for rule in current if rule != self.rule]
        else:
            raise ValueError(f"unknown edit op: {self.op}")
        return skill.with_rules(current)


def apply_edits(skill: Skill, edits) -> Skill:
    output = skill
    for edit in edits:
        output = edit.apply(output)
    return output
