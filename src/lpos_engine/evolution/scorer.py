"""Deterministic scorer for the CS-001 (human copy) style domain.

Why this domain for the pilot: it is one the review named as a good first
candidate, and it scores with no model call and no network, so the gate's
accept/reject behaviour is fully reproducible and auditable. A "skill" here is
the set of active lint rules; scoring is micro-averaged F1 of the rules the
skill actually catches against the real violations present in each task.

A GOOD rule fires only on genuine violations, so by construction a good rule
never produces a false positive. An OVERBROAD rule (the modelled bad edit) fires
on clean text too, so activating it lowers the score. This is what lets the pilot
demonstrate the gate rejecting a plausible-but-harmful edit.
"""
from __future__ import annotations

import re
from typing import Callable, Iterable, Mapping

_BANNED = re.compile(
    r"\b(seamless|effortless|unlock|supercharge|elevate|empower|game-?changing|"
    r"revolutioniz\w*|delve|robust|cutting-edge)\b",
    re.IGNORECASE,
)
_ANTITHESIS = re.compile(r"\bnot just\b.+?\b(it'?s|but)\b", re.IGNORECASE)
_TRIAD = re.compile(r"\b\w+, \w+,? and \w+\b")
_INT = re.compile(r"\b\d+\b")


def _number_parade(text: str) -> bool:
    return len(_INT.findall(text)) >= 3


# GOOD rules: each fires only on a genuine CS-001 violation.
GOOD_RULES: Mapping[str, Callable[[str], bool]] = {
    "em_dash": lambda t: "—" in t,
    "exclamation": lambda t: "!" in t,
    "banned_vocab": lambda t: bool(_BANNED.search(t)),
    "number_parade": _number_parade,
    "antithesis": lambda t: bool(_ANTITHESIS.search(t)),
    "triad": lambda t: bool(_TRIAD.search(t)),
}

# OVERBROAD rule: a plausible-sounding edit ("flag any very long word") that
# also fires on perfectly clean copy. Never a real violation; always an FP.
OVERBROAD_RULES: Mapping[str, Callable[[str], bool]] = {
    "long_word_overbroad": lambda t: any(len(w) > 12 for w in re.findall(r"[A-Za-z]+", t)),
}

ALL_RULES: dict[str, Callable[[str], bool]] = {**GOOD_RULES, **OVERBROAD_RULES}


def real_violations(text: str) -> set[str]:
    """Ground truth: the GOOD rules that genuinely fire on this text."""
    return {rid for rid, fn in GOOD_RULES.items() if fn(text)}


def score_skill(active_rules: Iterable[str], tasks: Iterable[dict]) -> float:
    """Micro-averaged F1 of caught real violations across tasks."""
    active = list(dict.fromkeys(active_rules))
    tp = fp = fn = 0
    for task in tasks:
        text = task["text"]
        expected = set(task["expected"])
        fired = {r for r in active if r in ALL_RULES and ALL_RULES[r](text)}
        tp += len(fired & expected)
        fp += len(fired - expected)
        fn += len(expected - fired)
    denom = 2 * tp + fp + fn
    return (2 * tp) / denom if denom else 1.0
