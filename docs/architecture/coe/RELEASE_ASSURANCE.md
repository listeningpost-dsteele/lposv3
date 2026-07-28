# COE Release Assurance

Release: LPOS 4.5.0

## One release identity

`release/release.json` is authoritative. `RELEASE.json`, `pyproject.toml`, and `lpos_engine.__version__` are mirrors. Identity drift blocks staging and release audit.

## Immutable application artifact

`lpos coe stage --repo <clean-source> --release-root <empty-external-directory>` copies tracked release inputs into an external staging directory, then generates `release-manifest.json` after staging is complete.

Every regular file except the manifest is recorded with its POSIX relative path, SHA-256, byte size, mode, and file type. The verifier rejects:

- missing listed files;
- extra unlisted files;
- content, size, or mode changes;
- absolute, traversal, duplicate, noncanonical, and case-colliding paths;
- symlinks;
- runtime state, status, reports, backups, caches, databases, logs, and credentials;
- release identity or source commit mismatch;
- malformed or empty manifests.

## Nine gates

1. Deterministic tests.
2. Application release verifier.
3. Doctor.
4. Engineering audit.
5. Security and reliability audit.
6. Documentation audit.
7. Bloat and efficiency audit.
8. Opportunity and value audit.
9. Release integrity and provenance.

Each gate is a child process invoked with an argument array, a bounded environment, timeout, and output ceiling. A zero exit without valid pass evidence is an error. Pass evidence with a nonzero process exit is an error.

The release controller is read-only with respect to checks. Any gap leaves the decision blocked.
