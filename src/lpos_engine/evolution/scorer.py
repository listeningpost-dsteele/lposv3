"""Deterministic scorer for the CS-001 human-copy domain.

The pilot uses this domain because it scores with no model call and no network,
so the gate's accept/reject behaviour is reproducible and auditable.
"""
from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Mapping

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


GOOD_RULES: Mapping[str, Callable[[str], bool]] = {
    "em_dash": lambda text: "\u2014" in text,
    "exclamation": lambda text: "!" in text,
    "banned_vocab": lambda text: bool(_BANNED.search(text)),
    "number_parade": _number_parade,
    "antithesis": lambda text: bool(_ANTITHESIS.search(text)),
    "triad": lambda text: bool(_TRIAD.search(text)),
}

OVERBROAD_RULES: Mapping[str, Callable[[str], bool]] = {
    "long_word_overbroad": lambda text: any(len(word) > 12 for word in re.findall(r"[A-Za-z]+", text)),
}

ALL_RULES: dict[str, Callable[[str], bool]] = {**GOOD_RULES, **OVERBROAD_RULES}


def real_violations(text: str) -> set[str]:
    """Ground truth: the GOOD rules that genuinely fire on this text."""
    return {rule_id for rule_id, fn in GOOD_RULES.items() if fn(text)}


def score_skill(active_rules: Iterable[str], tasks: Iterable[dict]) -> float:
    """Micro-averaged F1 of caught real violations across tasks."""
    active = list(dict.fromkeys(active_rules))
    true_positive = false_positive = false_negative = 0
    for task in tasks:
        text = task["text"]
        expected = set(task["expected"])
        fired = {rule for rule in active if rule in ALL_RULES and ALL_RULES[rule](text)}
        true_positive += len(fired & expected)
        false_positive += len(fired - expected)
        false_negative += len(expected - fired)
    denominator = 2 * true_positive + false_positive + false_negative
    return (2 * true_positive) / denominator if denominator else 1.0
