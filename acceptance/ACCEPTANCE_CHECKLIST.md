# LPOS COE Acceptance Checklist

Release: 4.5.0

Every item is closed only by a command exit, test, evidence hash, API response, external reference, artifact, or deployed URL probe.

- [ ] Hardcoded production pass results are absent.
- [ ] Complete staged-release manifest generated after final build.
- [ ] Missing, extra, changed, mutable, unsafe, and symlinked files fail verification.
- [ ] Release identity converges across every required mirror.
- [ ] Nine gates execute independently and emit schema-valid command evidence.
- [ ] Missing, stale, skipped, malformed, failed, or mismatched evidence blocks release.
- [ ] Daily 03:00 America/Chicago schedule is installed and read back.
- [ ] Audit ID and history persist in v4 SQLite.
- [ ] Engineering audit enumerates every changed file.
- [ ] Skill-search efficiency is measured or explicitly unknown with reason.
- [ ] Actual isolated backup restore passes.
- [ ] Scheduler and deterministic wake governance are measured.
- [ ] Storage trends persist by category.
- [ ] Technical debt and opportunities have lifecycle records.
- [ ] Private dashboard exposes all 18 named fields.
- [ ] Test report is delivered with provider acceptance evidence and dashboard link.
- [ ] GitHub, wiki, and Google Drive pass-off references are read back and verified.
- [ ] Final artifact is rebuilt, verified, pushed, deployed, and probed.

Implementation evidence is recorded under `docs/implementation-evidence/` and in the external COE state database.
