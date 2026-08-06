# LPOS 4.7 Behavioral Admission Test Suite Build Report

## Decision

**ACCEPT the admission harness and frozen test corpus for release sealing.**

This decision applies only to the test system and its 103 candidate suites. It does **not** admit, activate, or prove any Specialist.

## Build identity

- Repository: `listeningpost-dsteele/lposv3`
- Branch: `feature/4.7-expert-capability-system`
- Builder and corrective reviewer: Z.AI GLM 5/5.2 through the Hermes `zai` coding-plan provider
- Runtime roster bound by the corpus: 20 Guilds, 103 Specialists, 122 Craft Standards
- Generated admission suites: 103
- Generated behavioral cases: 824
- Required cases per Specialist: 8
- Mandatory cases: 618
- Held-out cases: 412
- Admission Python modules: 6
- New admission schemas: 3 root schemas with byte-identical packaged mirrors

## What was built

- Deterministic admission corpus generator derived from the exact Specialist charter, Guild charter, Craft Standards, invocation boundaries, methods, inputs, artifacts, dispositions, failure patterns, and completion criteria.
- One source-bound suite for every canonical runtime Specialist.
- Case coverage for representative positive work, positive routing, negative routing, adjacent-role confusion, missing inputs, capability gaps, authority boundaries, and weak-output/completion honesty.
- A competent evidence-aware generic baseline frozen by SHA-256.
- Deterministic prepare, blind, score, and verify phases.
- Explicit case × repetition × arm execution matrices with a frozen minimum of three repetitions.
- Anonymous A/B evaluator packets containing both arms, with the private assignment map kept separate.
- Frozen judgments before unblinding.
- Exact pass policy: dimension delta at least 0.25, overall delta at least 0.50, candidate win rate at least 0.60, all mandatory cases passing, and critical-failure veto.
- Evidence classes separating simulated component evidence, externally observed model execution, and provider-attested execution. Provider-attested evidence requires a bound attestation reference.
- Draft admission records only. The harness contains no automatic activation path.
- `lpos admission prepare|blind|score|verify` deterministic CLI commands.
- Corpus, schema, tamper, replay, blinding, scoring, evidence, and synthetic end-to-end tests.

## Anti-slop and evidence controls

The generator and validators reject:

- placeholder phrases such as “the required method,” “the required artifact,” and “apply the charter”;
- identity prose used as the substantive task;
- duplicated or overly generic task text;
- missing required case classes;
- duplicate suites or Specialist IDs;
- wrong Specialist, Guild, adjacent-role, or Craft Standard mappings;
- stale source hashes;
- incomplete, modified, replayed, duplicated, or cross-run outputs;
- arm-label or candidate-identity leakage;
- post-result threshold weakening;
- caller-shaped evidence upgrades;
- provider-attested claims without attestation;
- incomplete scoring judgments;
- mandatory-case failures and critical failures;
- activation claims in a draft admission record.

## Cross-Guild review

The GLM correction and adversarial review examined representative suites across all 20 Guilds. The final generator uses profession-specific charter sections rather than title substitution. It regenerates the complete corpus deterministically and the corpus validator reports no mapping, hash, adjacency, duplication, required-case, or anti-template errors.

Seven AI Guild charters do not contain an explicit “Prohibited shortcuts” section. For those roles, the generator uses their charter-specific characteristic failure patterns as the adversarial-boundary source. This remains source-bound but is a documented corpus limitation for a future charter revision.

## Verification performed before release sealing

```text
python tools/build_admission_corpus.py
Generated 103 admission suites

python -m pytest tests/test_admission.py -q
60 passed

validate_corpus(load_corpus_from_data())
{'valid': True, 'suite_count': 103, 'errors': []}

python -m pytest -q --deselect tests/test_v4_integrated_distribution.py::IntegratedV4DistributionTests::test_doctor_reports_one_healthy_v4_system
PASS
```

The manifest-dependent doctor test is expected to fail until the new immutable files are committed and `tools/reseal.py` is run. Existing release gates were not weakened.

## Files added or changed

- `src/lpos_engine/admission/`: models, generator, validator, harness, CLI, and packaged data
- `src/lpos_engine/admission/data/`: 103 Specialist suite files plus index
- `schemas/admission-*.schema.json`: three root schemas
- `src/lpos_engine/schemas/admission-*.schema.json`: three packaged mirrors
- `tests/test_admission.py`: 60 admission tests
- `tools/build_admission_corpus.py`: deterministic corpus build entry point
- `src/lpos_engine/cli.py`: `lpos admission` command registration
- `pyproject.toml`: admission package-data inclusion
- `verify_release.py`, `tests/test_schema_check.py`, and `tests/test_v4_integrated_distribution.py`: schema inventory update from 22 to 25

## Explicit limitations

- **No behavioral model executions have occurred.**
- **No Specialist has passed admission.**
- **No Specialist has been promoted to `proven_active`.**
- The suite constructs, freezes, blinds, scores, and verifies admission evidence; executing the candidate and baseline model runs is the next phase.
- Provider-attested qualification will require real provider execution receipts and independent blinded judgments.

## Release-sealing sequence

After committing the implementation inputs:

```bash
python3.11 tools/reseal.py
python3.11 verify_release.py
. /Users/dan/expert-cap-venv/bin/activate
python -m pytest
PYTHONPATH=src python -m lpos_engine doctor --db /tmp/lpos47-admission-doctor.db
```

A successful final run must show release integrity passed, 103 Specialists, and doctor status `healthy`.
