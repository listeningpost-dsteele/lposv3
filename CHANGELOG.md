# Changelog

## 4.1.0

- Added LPOS Skill Evolution, a validation-gated, staging-only capability for improving skills from reviewed evidence.
- Added `lpos_engine.evolution`, including deterministic CS-001 scoring, stable train/validation/test splitting, strict held-out gate, bounded edit proposal, LPOS fixture loading, and staging-only proposal output.
- Added the packaged `skill-evolution` Hermes skill so installers receive the capability with the distribution.
- Added `NOTICE-SKILLOPT.md` with Microsoft SkillOpt attribution under MIT and the LPOS adaptation boundary.
- Preserved offline defaults: no model calls, no network calls, no raw transcript harvesting, and no live skill writes.

## 4.0.0

- Initial integrated LPOS v4 operating-system distribution.
