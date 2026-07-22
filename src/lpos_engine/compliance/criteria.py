"""The codified SOC 2 framework: AICPA 2017 Trust Services Criteria (2022 POF).

This module encodes, as plain data, the framework the LPOS compliance engine
audits against: the AICPA Trust Services Criteria (TSC), 2017 edition with the
revised 2022 points of focus. The common criteria series CC1-CC9 apply to every
SOC 2 examination (they incorporate the COSO Internal Control framework); the
Security category is the common criteria themselves, and the optional
categories -- Availability (A), Confidentiality (C), Processing Integrity (PI),
and Privacy (P) -- add criteria when they are in scope for the system.

Type 1 versus Type 2. A SOC 2 **Type 1** report describes the system and
assesses whether controls are *suitably designed* at a single point in time.
A SOC 2 **Type 2** report goes further: it assesses whether those controls
*operated effectively* over an observation period (commonly 3-12 months).
Operating effectiveness cannot be observed in a single snapshot -- it is
demonstrated by repeated, evidenced control executions across the window.
That is why this engine keeps an append-only run history per control and
computes an effectiveness ratio over :data:`OBSERVATION_WINDOW_DAYS` (default
90 days) rather than reporting only the current pass/fail state.

Nothing here is an attestation. A SOC 2 report is issued by an independent
CPA firm; this module is the machine-readable control framework the LPOS
system holds itself to, continuously.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Length of the Type 2 observation window, in days. Operating effectiveness
#: is computed over check-run history within this window.
OBSERVATION_WINDOW_DAYS = 90

#: The framework identifier used in every status document this engine writes.
FRAMEWORK = "SOC 2 Type 2 (TSC 2017, 2022 POF)"


@dataclass(frozen=True, slots=True)
class Criterion:
    """One Trust Services Criteria series or category, as data."""

    id: str
    title: str
    description: str


CRITERIA: tuple[Criterion, ...] = (
    Criterion(
        id="CC1",
        title="Control Environment",
        description=(
            "The entity demonstrates a commitment to integrity and ethical values, "
            "exercises oversight of the development and performance of internal "
            "control, establishes structures, reporting lines, authorities, and "
            "responsibilities, and holds individuals accountable. For LPOS this "
            "means the operating specification itself: the core spec, the guild "
            "structure that assigns responsibility, and honest attribution of "
            "derived work."
        ),
    ),
    Criterion(
        id="CC2",
        title="Communication and Information",
        description=(
            "The entity obtains or generates and uses relevant, quality information "
            "to support the functioning of internal control, and communicates that "
            "information internally and externally, including objectives and "
            "responsibilities. For LPOS this is the shipped documentation surface: "
            "the README, the wiki, and per-release patch notes that tell operators "
            "exactly what changed."
        ),
    ),
    Criterion(
        id="CC3",
        title="Risk Assessment",
        description=(
            "The entity specifies objectives with sufficient clarity to enable the "
            "identification and assessment of risks, identifies and analyzes risks "
            "to the achievement of its objectives, considers the potential for "
            "fraud, and identifies and assesses changes that could significantly "
            "affect internal control. For LPOS this is a maintained threat model "
            "and security posture document."
        ),
    ),
    Criterion(
        id="CC4",
        title="Monitoring Activities",
        description=(
            "The entity selects, develops, and performs ongoing and/or separate "
            "evaluations to ascertain whether the components of internal control "
            "are present and functioning, and evaluates and communicates internal "
            "control deficiencies in a timely manner. For LPOS this is controls "
            "that watch other controls: the documentation drift audit and this "
            "compliance Standing Operation itself."
        ),
    ),
    Criterion(
        id="CC5",
        title="Control Activities",
        description=(
            "The entity selects and develops control activities that contribute to "
            "the mitigation of risks to acceptable levels, including general "
            "controls over technology, and deploys them through policies and "
            "procedures. For LPOS the primary control activities are its automated "
            "test suite and its immutable benchmark corpus, which gate every "
            "release."
        ),
    ),
    Criterion(
        id="CC6",
        title="Logical and Physical Access Controls",
        description=(
            "The entity implements logical access security software, "
            "infrastructure, and architectures over protected information assets; "
            "restricts logical and physical access; manages credentials; and "
            "protects against threats from sources outside its system boundaries. "
            "For LPOS this is loopback-only service binding, the exact-action "
            "approval gate on privileged operations, and secrets hygiene "
            "(credentials referenced by file, never inline)."
        ),
    ),
    Criterion(
        id="CC7",
        title="System Operations",
        description=(
            "The entity uses detection and monitoring procedures to identify "
            "changes and susceptibilities to vulnerabilities, monitors system "
            "components for anomalies indicative of malicious acts or errors, "
            "evaluates security events, and responds to and recovers from "
            "identified incidents. For LPOS this is the hourly connector health "
            "monitor, its published status document, and the append-only event "
            "store that makes every state change auditable."
        ),
    ),
    Criterion(
        id="CC8",
        title="Change Management",
        description=(
            "The entity authorizes, designs, develops or acquires, configures, "
            "documents, tests, approves, and implements changes to infrastructure, "
            "data, software, and procedures. For LPOS this is the release "
            "discipline: a changelog entry, a signed manifest and checksums, "
            "release verification tooling, and the SO-022 publication workflow "
            "with its documentation gate."
        ),
    ),
    Criterion(
        id="CC9",
        title="Risk Mitigation",
        description=(
            "The entity identifies, selects, and develops risk mitigation "
            "activities for risks arising from potential business disruptions, and "
            "assesses and manages risks associated with vendors and business "
            "partners. For LPOS this is the rollback path: complete self-contained "
            "releases, retained prior versions and wheels, and a documented "
            "restore procedure."
        ),
    ),
    Criterion(
        id="A",
        title="Availability",
        description=(
            "Information and systems are available for operation and use to meet "
            "the entity's objectives: capacity management, environmental "
            "protections, and recovery infrastructure including backups and "
            "restoration testing. For LPOS this is state-database integrity "
            "checking and a documented backup and restore procedure."
        ),
    ),
    Criterion(
        id="C",
        title="Confidentiality",
        description=(
            "Information designated as confidential is protected to meet the "
            "entity's objectives: identification, retention, and secure disposal "
            "of confidential information. For LPOS this is the record-only default "
            "for external actions (nothing leaves the system without an explicit, "
            "approved plan) and the subprocess adapter boundary that keeps model "
            "backends isolated from the control plane."
        ),
    ),
    Criterion(
        id="PI",
        title="Processing Integrity",
        description=(
            "System processing is complete, valid, accurate, timely, and "
            "authorized to meet the entity's objectives: inputs, processing, and "
            "outputs are quality-assured. For LPOS this is idempotency-keyed "
            "workflow execution (a run happens exactly once per schedule key) and "
            "canonical digests over frozen step outputs, so evidence cannot drift "
            "after the fact."
        ),
    ),
    Criterion(
        id="P",
        title="Privacy",
        description=(
            "Personal information is collected, used, retained, disclosed, and "
            "disposed of to meet the entity's objectives: notice, choice and "
            "consent, access, disclosure, quality, and monitoring. LPOS processes "
            "the operator's own working data locally; no privacy-specific "
            "machine-checkable control ships in this catalog yet, so the P "
            "category is encoded for completeness and marked out of scope."
        ),
    ),
)

#: Fast lookup by criterion id.
CRITERIA_BY_ID: dict[str, Criterion] = {criterion.id: criterion for criterion in CRITERIA}


def criterion(criterion_id: str) -> Criterion:
    """Return the criterion for an id like ``CC8`` (raises KeyError if unknown)."""

    return CRITERIA_BY_ID[criterion_id]
