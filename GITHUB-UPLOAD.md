# Publish This Repository to GitHub

The repository is git-native now; prefer SO-022 Release Publication or a
plain push over drag-and-drop.

1. Edit sources under `Source/v3/`, then run:
   `python3 Tools/compile.py && python3 Tools/build_release.py <version>`
2. Run `python3 Tests/verify_compact.py` and `python3 Tests/mutation_test.py`.
3. Commit with: `Release LPOS v3.3` (match the MANIFEST version).
4. Push to the `lposv3` repository. CI re-runs every check on the commit.

Manual fallback: GitHub web upload of the full folder, same commit message.
The Hermes-ready package is `Build/LPOS-Hermes-Compact-v3.3.zip`.
