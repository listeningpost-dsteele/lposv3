"""A skill as a bounded, ordered set of active rules, plus edit operations.

This is the abstract stand-in for a `SKILL.md`: what matters for the pilot is
that a skill is a set of rules the scorer can run, that edits are explicit and
budgeted (SkillOpt's "textual learning rate": few edits per candidate so change
stays legible), and that a skill renders to a reviewable document a human signs
off before anything is adopted.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

from .scorer import ALL_RULES


@dataclass(frozen=True)
class Skill:
    name: str
    rules: tuple[str, ...] = field(default_factory=tuple)

    def with_rules(self, rules) -> "Skill":
        ordered = tuple(dict.fromkeys(rules))
        for r in ordered:
            if r not in ALL_RULES:
                raise ValueError(f"unknown rule: {r}")
        return replace(self, rules=ordered)

    def render(self) -> str:
        lines = [f"# {self.name}", "", "Active CS-001 checks:", ""]
        lines += [f"- {r}" for r in self.rules] or ["- (none)"]
        return "\n".join(lines) + "\n"


@dataclass(frozen=True)
class Edit:
    op: str        # "add" | "remove"
    rule: str
    rationale: str

    def apply(self, skill: Skill) -> Skill:
        cur = list(skill.rules)
        if self.op == "add":
            if self.rule not in cur:
                cur.append(self.rule)
        elif self.op == "remove":
            cur = [r for r in cur if r != self.rule]
        else:
            raise ValueError(f"unknown edit op: {self.op}")
        return skill.with_rules(cur)


def apply_edits(skill: Skill, edits) -> Skill:
    out = skill
    for e in edits:
        out = e.apply(out)
    return out
