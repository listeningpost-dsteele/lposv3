#!/usr/bin/env python3
"""Release signing and verification (LPOS-11).

Checksums prove internal consistency; they do not prove who published the tree —
anyone who can modify the release can regenerate RELEASE-MANIFEST.json and
SHA256SUMS. This tool binds the release to a signing identity held OFFLINE,
outside the runtime account:

    # one-time, on a protected machine:
    python tools/sign_release.py keygen --key-dir /secure/lpos-signing

    # each release (after tools/reseal.py):
    python tools/sign_release.py sign --key /secure/lpos-signing/lpos-signing.pem

    # anyone, with the published public key:
    python tools/sign_release.py verify --pub RELEASE-PUBKEY.pem

Uses Ed25519 via the system `openssl` binary (no Python dependencies). The
signature covers the SHA-256 digest of RELEASE-MANIFEST.json, which itself hashes
every immutable file — so one signature covers the whole tree. The public key
(RELEASE-PUBKEY.pem) ships in the tree; the expected archive digest and the
public key fingerprint should ALSO be published through an independent channel
(e.g. the project page at chip.listeningpost.ai) so a swapped-in key is
detectable. verify_release.py calls the verify path automatically when a
signature is present.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "RELEASE-MANIFEST.json"
SIGNATURE = ROOT / "RELEASE-SIGNATURE.bin"
PUBKEY = ROOT / "RELEASE-PUBKEY.pem"


def _openssl() -> str:
    exe = shutil.which("openssl")
    if not exe:
        raise SystemExit("openssl is required for release signing/verification")
    return exe


def manifest_digest() -> bytes:
    return hashlib.sha256(MANIFEST.read_bytes()).digest()


def keygen(key_dir: Path) -> int:
    key_dir.mkdir(parents=True, exist_ok=True)
    key = key_dir / "lpos-signing.pem"
    if key.exists():
        raise SystemExit(f"refusing to overwrite existing key: {key}")
    subprocess.run([_openssl(), "genpkey", "-algorithm", "ed25519", "-out", str(key)], check=True)
    key.chmod(0o600)
    subprocess.run(
        [_openssl(), "pkey", "-in", str(key), "-pubout", "-out", str(key_dir / "lpos-signing.pub.pem")],
        check=True,
    )
    print(f"signing key: {key} (keep offline; mode 0600)")
    print(f"public key:  {key_dir / 'lpos-signing.pub.pem'} (publish; copy into the tree as RELEASE-PUBKEY.pem)")
    return 0


def sign(key: Path) -> int:
    digest_file = ROOT / ".manifest-digest.tmp"
    digest_file.write_bytes(manifest_digest())
    try:
        subprocess.run(
            [_openssl(), "pkeyutl", "-sign", "-inkey", str(key), "-rawin",
             "-in", str(digest_file), "-out", str(SIGNATURE)],
            check=True,
        )
    finally:
        digest_file.unlink(missing_ok=True)
    subprocess.run([_openssl(), "pkey", "-in", str(key), "-pubout", "-out", str(PUBKEY)], check=True)
    print(f"signed RELEASE-MANIFEST.json digest -> {SIGNATURE.name}; public key -> {PUBKEY.name}")
    print("re-run tools/reseal.py is NOT needed (signature files are excluded from the manifest)")
    return 0


def verify(pub: Path) -> int:
    if not SIGNATURE.is_file():
        print("UNSIGNED: no RELEASE-SIGNATURE.bin present")
        return 2
    digest_file = ROOT / ".manifest-digest.tmp"
    digest_file.write_bytes(manifest_digest())
    try:
        completed = subprocess.run(
            [_openssl(), "pkeyutl", "-verify", "-pubin", "-inkey", str(pub), "-rawin",
             "-in", str(digest_file), "-sigfile", str(SIGNATURE)],
            capture_output=True, text=True,
        )
    finally:
        digest_file.unlink(missing_ok=True)
    ok = completed.returncode == 0
    print("signature VALID" if ok else f"signature INVALID: {completed.stderr.strip()}")
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    k = sub.add_parser("keygen"); k.add_argument("--key-dir", type=Path, required=True)
    s = sub.add_parser("sign"); s.add_argument("--key", type=Path, required=True)
    v = sub.add_parser("verify"); v.add_argument("--pub", type=Path, default=PUBKEY)
    args = parser.parse_args()
    if args.cmd == "keygen":
        return keygen(args.key_dir)
    if args.cmd == "sign":
        return sign(args.key)
    return verify(args.pub)


if __name__ == "__main__":
    raise SystemExit(main())
