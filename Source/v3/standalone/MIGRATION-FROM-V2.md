# Migration from LPOS v2 (run ONLY when upgrading an existing v2 Hermes environment)

Fresh installs use INSTALL-LPOS-COMPACT.md alone and SKIP this file.

1. Back up current capabilities, cron jobs, prompts, project state, and active
   artifact versions before changing anything.
2. Map every existing capability to a Guild, Specialist (via SPECIALIST-INDEX.md),
   and craft standard (via CRAFT-STANDARD-ROUTING.yaml).
3. Preserve valuable domain knowledge from existing capabilities.
4. Migrate any existing evidence, decisions, and Principal context into the
   `lpos-state/` formats defined in LEDGERS.md.
5. Repoint every scheduled job to the canonical install path (for example the
   `current` symlink); verify one manual run per job before trusting its schedule.
6. Remove generic or conflicting legacy instructions only after a verified
   replacement exists. Verify through real execution, not configuration.
7. Pause legacy components only after verified replacement; keep rollback paths.
   Mark superseded source trees with a DEPRECATED marker instead of deleting them.
8. Do not publish, send, deploy, purchase, delete, or perform another irreversible
   external action without explicit approval.

Environment-specific remediation (for example, restoring a previously degraded
artifact) is a session instruction from the Principal, never part of this
distribution. Report results using the completion report format in
INSTALL-LPOS-COMPACT.md.
