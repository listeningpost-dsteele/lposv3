---
title: Install LPOS
section: getting-started
order: 2
---

# Install LPOS

You want a working LPOS installation on your machine. The whole process is: extract the release ZIP into a new directory, run one installer from that directory, and let it verify itself.

## Step 1: Extract the release

Extract the release ZIP into a new, empty directory. Everything LPOS needs lives inside this one self-contained directory — the installer never writes outside it.

## Step 2: Run the installer

From inside the extracted directory:

**macOS or Linux**

```bash
bash INSTALL.sh
```

**Windows PowerShell**

```powershell
.\INSTALL.ps1
```

**Any platform**

```bash
python install.py
```

All three routes run the same Python installer. Two optional flags:

- `--skip-demo` installs and initializes LPOS without running the record-only verification flow at the end.
- `--reset-environment` deletes and recreates the local `.venv` before installation (useful when re-installing over a broken environment).

## What the installer does

The installer is deliberately transparent — it prints each command before running it. In order, it:

1. **Verifies the release** by running `verify_release.py`, which checks every file against the SHA-256 manifest, confirms version synchronization across the release metadata, registry, and workflow catalog, and validates the 32 specialists, 21 Standing Operations, 53 benchmarks, and 17 schemas.
2. **Creates a local Python environment** at `.venv` inside the release directory (or reuses an existing one).
3. **Installs the bundled wheel offline** with `pip install --no-index`, then runs `pip check`.
4. **Smoke-tests the CLI**: `lpos version` and `lpos validate-schemas` via the module form.
5. **Initializes the state database** at `state/lpos.db` with `lpos init`, applying the checksummed migrations.
6. **Runs `lpos doctor`** against the new database to confirm the integrated specification, runtime assets, and database are healthy.
7. **Runs the record-only verification flow** (`lpos demo`) into `state/verification/` — a complete end-to-end task with interpretation contract, artifact, exact-action approval, and isolated review, with no real side effects. Skipped if you passed `--skip-demo`.

## Step 3: Confirm it worked

```bash
.venv/bin/lpos version
.venv/bin/lpos doctor --db state/lpos.db
```

On Windows:

```powershell
.\.venv\Scripts\lpos.exe version
.\.venv\Scripts\lpos.exe doctor --db state\lpos.db
```

`doctor` should report `"status": "healthy"` with 32 specialists, 21 standing operations, and 53 benchmarks. The direct module form also works anywhere: `.venv/bin/python -m lpos_engine --help`.

## If the installer stops

The installer fails loudly and early rather than leaving a half-installed system:

- **"Python 3.11+ is required; found ..."** — install a newer Python and re-run.
- **"RELEASE.json is missing or invalid"** — the extraction is incomplete or you are running from the wrong directory; re-extract and run from the bundle root.
- **"LPOS v4 release verification FAILED"** with a list of files — the bundle is modified or corrupted; re-download and re-extract. (Note for later: adding your own files to the release directory also triggers this, because the manifest lists every immutable file.)
- **"virtual-environment Python was not created"** — your Python cannot create venvs; check that the `venv` module is available.

More in [Troubleshooting](/administration/troubleshooting.html).

## Related pages

- [Requirements](/getting-started/requirements.html)
- [Onboarding walkthrough](/getting-started/onboarding.html)
- [Your first hour](/getting-started/first-hour.html)
- [Upgrading](/administration/upgrading.html)
