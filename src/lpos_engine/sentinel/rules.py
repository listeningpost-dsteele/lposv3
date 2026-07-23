"""Conservative, non-destructive Sentinel artifact checks.

These checks are deliberately static and read-only.  They identify high-signal
security anti-patterns in text artifacts without executing the artifact, opening
network connections, invoking a shell, or copying sensitive evidence into the ledger.
Active penetration testing requires a separately approved and isolated engagement.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Pattern, Sequence

from ..canonical import new_id, text_digest, utc_now
from ..models import Artifact
from .models import (
    FindingEvidence,
    RemediationPlan,
    SecurityAssessment,
    SecurityFinding,
    SENTINEL_POLICY_VERSION,
    sort_findings,
)


@dataclass(frozen=True, slots=True)
class RuleDefinition:
    rule_id: str
    severity: str
    category: str
    title: str
    description: str
    patterns: tuple[Pattern[str], ...]
    remediation: RemediationPlan
    confidence: float = 0.9


def _rx(pattern: str, flags: int = re.IGNORECASE) -> Pattern[str]:
    return re.compile(pattern, flags)


RULES: tuple[RuleDefinition, ...] = (
    RuleDefinition(
        "SENT-001",
        "critical",
        "secrets",
        "Private-key material embedded in an artifact",
        "The artifact appears to contain private-key material. Exposure can permit impersonation or decryption.",
        (_rx(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----", 0),),
        RemediationPlan(
            "Remove and rotate the exposed private key.",
            (
                "Delete the key material from the artifact and every derived copy.",
                "Revoke or rotate the affected key through the authoritative key-management system.",
                "Replace embedded credentials with a secret-manager reference and least-privileged runtime access.",
            ),
            (
                "Re-run secret scanning over the corrected artifact and its history.",
                "Verify the old key is rejected and the replacement is scoped, logged, and rotated.",
            ),
        ),
        0.99,
    ),
    RuleDefinition(
        "SENT-002",
        "high",
        "secrets",
        "Likely hard-coded credential",
        "A credential-like value appears to be assigned directly in the artifact instead of retrieved from an approved secret store.",
        (
            _rx(r"\b(?:api[_-]?key|client[_-]?secret|access[_-]?token|auth[_-]?token|password|passwd|secret)\b\s*[:=]\s*[\"'][^\"']{8,}[\"']"),
            _rx(r"\bAKIA[0-9A-Z]{16}\b", 0),
            _rx(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b", 0),
        ),
        RemediationPlan(
            "Remove the credential and rotate it before use.",
            (
                "Replace the literal with a reference to an approved secret manager or injected environment value.",
                "Rotate the potentially exposed credential and reduce its permissions and lifetime.",
                "Prevent recurrence with pre-commit and CI secret scanning.",
            ),
            (
                "Confirm no credential value remains in the artifact or version history.",
                "Verify the rotated credential works only for its intended principal and scope.",
            ),
        ),
        0.93,
    ),
    RuleDefinition(
        "SENT-003",
        "high",
        "command_execution",
        "Unsafe shell execution path",
        "The artifact invokes a shell or operating-system command in a way that can turn untrusted input into command execution.",
        (
            _rx(r"\bshell\s*=\s*True\b", 0),
            _rx(r"\bos\.system\s*\("),
            _rx(r"\b(?:popen|system)\s*\([^)]*(?:input|request|param|args|user)"),
        ),
        RemediationPlan(
            "Eliminate shell interpretation and pass fixed argument arrays to a constrained subprocess API.",
            (
                "Replace shell execution with a direct executable and an explicit argument list.",
                "Allowlist commands and validate each argument independently of the shell.",
                "Run the operation under a least-privileged account in a restricted sandbox.",
            ),
            (
                "Exercise metacharacter, quoting, and path-injection test cases and confirm they remain inert.",
                "Verify the runtime never starts an intermediary shell for the action.",
            ),
        ),
        0.94,
    ),
    RuleDefinition(
        "SENT-004",
        "critical",
        "supply_chain",
        "Downloaded content is piped directly to a shell",
        "A network download appears to be executed before its identity or integrity is verified.",
        (_rx(r"\b(?:curl|wget)\b[^\n|;]*(?:\||;)\s*(?:sudo\s+)?(?:sh|bash|zsh)\b"),),
        RemediationPlan(
            "Separate download, verification, and execution.",
            (
                "Download to a non-executable temporary file over authenticated TLS.",
                "Verify a pinned publisher signature and expected cryptographic digest.",
                "Inspect and execute only the verified artifact in a disposable least-privileged environment.",
            ),
            (
                "Tamper with the downloaded bytes and confirm execution is refused.",
                "Confirm the verified publisher identity and digest are recorded in release evidence.",
            ),
        ),
        0.99,
    ),
    RuleDefinition(
        "SENT-005",
        "high",
        "unsafe_deserialization",
        "Dynamic code execution or unsafe deserialization",
        "The artifact uses an API that may execute attacker-controlled code or object constructors.",
        (
            _rx(r"\b(?:eval|exec)\s*\("),
            _rx(r"\bpickle\.(?:load|loads)\s*\("),
            _rx(r"\byaml\.load\s*\([^\n]*Loader\s*=\s*yaml\.(?:Loader|FullLoader)"),
        ),
        RemediationPlan(
            "Replace dynamic execution with a data-only parser and explicit dispatch.",
            (
                "Use a schema-validated data format that cannot instantiate arbitrary objects.",
                "Replace eval/exec with an allowlisted parser or operation map.",
                "Treat all serialized input as untrusted and authenticate its origin and integrity.",
            ),
            (
                "Run malicious-object and expression payloads and confirm no code executes.",
                "Verify invalid or unknown operations fail closed with an audit event.",
            ),
        ),
        0.96,
    ),
    RuleDefinition(
        "SENT-006",
        "high",
        "injection",
        "SQL query appears to interpolate data",
        "A query string appears to be built with string interpolation, which can permit SQL injection.",
        (
            _rx(r"(?:execute|executemany)\s*\(\s*f[\"']"),
            _rx(r"(?:SELECT|INSERT|UPDATE|DELETE)\b[^\n]*(?:%s|\.format\s*\(|\{[^}]+\})"),
        ),
        RemediationPlan(
            "Use parameterized statements and a least-privileged database identity.",
            (
                "Move every data value into the database driver's parameter-binding mechanism.",
                "Allowlist any identifier that cannot be parameterized, such as a column name.",
                "Limit the database account to only the statements and objects required.",
            ),
            (
                "Run quote, comment, boolean, and stacked-query injection cases.",
                "Confirm query structure remains constant and only bound values change.",
            ),
        ),
        0.91,
    ),
    RuleDefinition(
        "SENT-007",
        "high",
        "transport_security",
        "TLS certificate verification is disabled",
        "The artifact disables peer verification, permitting interception and endpoint impersonation.",
        (
            _rx(r"\bverify\s*=\s*False\b", 0),
            _rx(r"CERT_NONE|check_hostname\s*=\s*False"),
            _rx(r"NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*[\"']?0"),
        ),
        RemediationPlan(
            "Restore certificate and hostname verification.",
            (
                "Remove the verification bypass and use the platform trust store or a pinned approved CA.",
                "Correct certificate deployment rather than suppressing validation errors.",
                "Add explicit timeouts and safe failure handling for the connection.",
            ),
            (
                "Confirm an untrusted, expired, or wrong-host certificate is rejected.",
                "Confirm the approved endpoint succeeds with verification enabled.",
            ),
        ),
        0.97,
    ),
    RuleDefinition(
        "SENT-008",
        "medium",
        "cryptography",
        "Weak or obsolete cryptographic primitive",
        "The artifact references a primitive that should not protect credentials, signatures, or security-sensitive integrity.",
        (
            _rx(r"\b(?:md5|sha1)\s*\("),
            _rx(r"hashlib\.(?:md5|sha1)\s*\("),
            _rx(r"\bDES(?:3)?\b|\bRC4\b"),
        ),
        RemediationPlan(
            "Use a current, purpose-specific cryptographic construction.",
            (
                "Use an approved modern password KDF, MAC, signature, or hash for the actual purpose.",
                "Centralize cryptographic choices in a reviewed library and configuration.",
                "Plan migration for existing data or tokens protected by the obsolete primitive.",
            ),
            (
                "Add known-answer tests for the replacement construction.",
                "Verify legacy values are migrated or rejected according to the approved transition plan.",
            ),
        ),
        0.85,
    ),
    RuleDefinition(
        "SENT-009",
        "medium",
        "permissions",
        "Overly permissive file mode",
        "The artifact appears to create a world-writable or broadly readable sensitive file.",
        (
            _rx(r"\b(?:chmod|mode\s*=)\s*\(?\s*0?777\b"),
            _rx(r"\bos\.chmod\s*\([^\n,]+,\s*0o?777\b"),
            _rx(r"\bumask\s*\(?\s*0\s*\)?"),
        ),
        RemediationPlan(
            "Apply least-privilege ownership and modes.",
            (
                "Create private directories as 0700 and sensitive files as 0600 unless a narrower documented exception applies.",
                "Set permissions atomically at creation instead of correcting them later.",
                "Validate ownership and reject symlink substitution at trust boundaries.",
            ),
            (
                "Inspect resulting modes and ownership under the deployment user's default umask.",
                "Attempt access from an unrelated local account and confirm it is denied.",
            ),
        ),
        0.88,
    ),
    RuleDefinition(
        "SENT-010",
        "high",
        "agent_control_plane",
        "Instruction attempts to bypass LPOS controls",
        "The artifact contains a directive that appears to disable approval, policy, review, authentication, or safety controls.",
        (
            _rx(r"\b(?:ignore|bypass|disable|skip|override)\b[^\n]{0,80}\b(?:approval|policy|review|authentication|authorization|guardrail|safety|constitution)\b"),
            _rx(r"\bdo not (?:log|audit|report)\b"),
            _rx(r"\bpretend (?:the )?(?:principal|administrator|owner) approved\b"),
        ),
        RemediationPlan(
            "Treat the directive as untrusted data and preserve control-plane enforcement.",
            (
                "Remove executable authority from model- or artifact-supplied instructions.",
                "Bind approvals to verified identity and the exact action hash in deterministic code.",
                "Keep the suspect content in a quoted data boundary and record the attempted control bypass.",
            ),
            (
                "Replay the directive and confirm it cannot change policy, approval, review, or logging behavior.",
                "Verify the attempt creates an immutable audit event and an independently reviewed alert.",
            ),
        ),
        0.9,
    ),
)

RULE_IDS = tuple(rule.rule_id for rule in RULES)

_SECRET_ASSIGNMENT = re.compile(
    r"(?i)(\b(?:api[_-]?key|client[_-]?secret|access[_-]?token|auth[_-]?token|password|passwd|secret)\b\s*[:=]\s*)[\"'][^\"']+[\"']"
)
_TOKEN_PATTERNS = (
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
)
_PLACEHOLDER_VALUES = {
    "example",
    "example-value",
    "changeme",
    "change-me",
    "placeholder",
    "redacted",
    "not-a-real-secret",
    "your-secret-here",
}


def redact_excerpt(line: str) -> str:
    """Return a bounded excerpt that cannot reproduce common credential forms."""

    if "PRIVATE KEY-----" in line:
        return "[REDACTED PRIVATE KEY MATERIAL]"
    value = _SECRET_ASSIGNMENT.sub(r"\1\"[REDACTED]\"", line)
    for pattern in _TOKEN_PATTERNS:
        value = pattern.sub("[REDACTED TOKEN]", value)
    value = value.strip()
    if not value:
        value = "[REDACTED EVIDENCE]"
    return value[:1_000]


def _looks_like_placeholder(line: str) -> bool:
    lowered = line.lower()
    return any(token in lowered for token in _PLACEHOLDER_VALUES) or "${" in line or "<secret" in lowered


class SentinelScanner:
    """Deterministic static scanner for one exact artifact revision."""

    def __init__(self, *, blocking_severities: Sequence[str] = ("critical", "high")) -> None:
        self.blocking_severities = frozenset(blocking_severities)

    @property
    def rule_ids(self) -> tuple[str, ...]:
        return RULE_IDS

    def scan_artifact(
        self,
        artifact: Artifact,
        *,
        assessment_id: str | None = None,
        trigger: str = "artifact_created",
        mode: str = "passive",
    ) -> SecurityAssessment:
        assessment_id = assessment_id or new_id("SASSESS")
        started = utc_now()
        lines = artifact.content.splitlines() or (artifact.content,)
        findings: list[SecurityFinding] = []

        for rule in RULES:
            evidence: list[FindingEvidence] = []
            seen: set[str] = set()
            for line_number, line in enumerate(lines, start=1):
                if rule.rule_id == "SENT-002" and _looks_like_placeholder(line):
                    continue
                if not any(pattern.search(line) for pattern in rule.patterns):
                    continue
                evidence_hash = text_digest(f"{line_number}:{line}")
                if evidence_hash in seen:
                    continue
                seen.add(evidence_hash)
                evidence.append(
                    FindingEvidence(
                        kind="static_pattern",
                        location=f"line:{line_number}",
                        redacted_excerpt=redact_excerpt(line),
                        evidence_hash=evidence_hash,
                    )
                )
                if len(evidence) >= 10:
                    break
            if evidence:
                findings.append(
                    SecurityFinding.create(
                        finding_id=new_id("SFIND"),
                        assessment_id=assessment_id,
                        task_id=artifact.task_id,
                        artifact_id=artifact.artifact_id,
                        artifact_hash=artifact.content_hash,
                        rule_id=rule.rule_id,
                        severity=rule.severity,
                        category=rule.category,
                        title=rule.title,
                        description=rule.description,
                        evidence=evidence,
                        remediation=rule.remediation,
                        confidence=rule.confidence,
                        blocking=rule.severity in self.blocking_severities,
                    )
                )

        ordered = sort_findings(findings)
        return SecurityAssessment(
            assessment_id=assessment_id,
            task_id=artifact.task_id,
            artifact_id=artifact.artifact_id,
            artifact_hash=artifact.content_hash,
            scope="artifact",
            mode=mode,
            trigger=trigger,
            policy_version=SENTINEL_POLICY_VERSION,
            status="findings" if ordered else "clean",
            checked_rules=RULE_IDS,
            findings=ordered,
            limitations=(
                "Passive static analysis only; the artifact was not executed.",
                "No network, exploitation, credential use, persistence, or destructive probe was performed.",
                "Active penetration testing requires a separate Principal-approved scope and isolated environment.",
            ),
            isolated=True,
            started_at=started,
            completed_at=utc_now(),
        )


def finding_signatures(assessment: SecurityAssessment) -> tuple[tuple[str, str, bool, str], ...]:
    """Stable signatures used by the independent structural re-scan."""

    return tuple(
        sorted(
            (finding.rule_id, finding.severity, finding.blocking, finding.fingerprint)
            for finding in assessment.findings
        )
    )
