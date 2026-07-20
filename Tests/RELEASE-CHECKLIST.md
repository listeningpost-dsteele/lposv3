# LPOS Compact Release Checklist (v3.3)

Every line names its enforcement. Manual-only lines require a human initial.

- [ ] Sources edited under `Source/v3/` only — enforced: `Tools/compile.py --check` in CI.
- [ ] Compiled output reproducible — enforced: compile roundtrip check in CI.
- [ ] Zip opens and matches `Build/Hermes` byte-for-byte — enforced: validator archive check.
- [ ] Manifest SHA-256 hashes current — enforced: validator + `build_release.py --check`.
- [ ] All component schemas valid; no duplicate ids or slugs — enforced: validator.
- [ ] Reference graph resolves (standards, guilds, specialists, SOs, benchmarks, index) — enforced: validator.
- [ ] Safety content present (approval guard, review envelope, self-approval ban, SO-021 behaviors, CS-003 default) — enforced: validator.
- [ ] 16-case mutation suite rejects all sabotage variants — enforced: `Tests/mutation_test.py` in CI.
- [ ] No secrets or hardcoded identity — enforced: validator scan.
- [ ] Version consistent across MANIFEST, CHANGELOG, kernel — enforced: validator.
- [ ] Fixture coverage at or above the floor — enforced: validator (floor may only rise).
- [ ] Clean-install smoke test in a fresh Hermes session — manual: ____
- [ ] Drive link still downloads the new package — manual: ____
