#!/usr/bin/env python3
"""Fail when tracked content contains an OpenAI-style API key.

CI and pre-commit run this against the git checkout. ``--self-test``
writes a key-shaped string to a temporary file outside the repository
and checks that the scan rejects it. That file is the fixture: it is
not committed, because a committed key must fail this gate.

The live OpenAI API is not called.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# Legacy keys are a long alphanumeric token. Current project, admin,
# and service-account keys keep a prefix and a url-safe secret.
# "sk-test-not-a-real-key" and Stripe's "sk_test_..." do not match.
_LEGACY = re.compile(rb"sk-[A-Za-z0-9]{32,}")
_PREFIXED = re.compile(rb"sk-(?:proj|admin|svcacct)-[A-Za-z0-9_-]{20,}")
_PATTERNS = (_LEGACY, _PREFIXED)


def project_key():
    """A project-key shape. Built so this source file is not a match."""
    return "sk-" + "proj-" + ("aB3x" * 16)


def legacy_key():
    """A legacy key shape, including the OpenAI marker, built the same way."""
    return "sk-" + ("Ab" * 20) + "T3BlbkFJ" + ("Cd" * 20)


def _git_toplevel(start):
    result = subprocess.run(
        ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip())


def iter_files(root):
    """Tracked files when ``root`` is a git toplevel; otherwise every file."""
    root = root.resolve()
    toplevel = _git_toplevel(root)
    if toplevel is not None and toplevel.resolve() == root:
        listed = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            capture_output=True,
            check=True,
        )
        files = []
        for name in listed.stdout.split(b"\0"):
            if not name:
                continue
            path = root / name.decode()
            if path.is_file():
                files.append(path)
        return files
    return [path for path in root.rglob("*") if path.is_file()]


def scan(root):
    """Return ``path:line`` findings. The matched text is not included."""
    findings = []
    for path in iter_files(root):
        data = path.read_bytes()
        line_numbers = set()
        for pattern in _PATTERNS:
            for match in pattern.finditer(data):
                line_numbers.add(data.count(b"\n", 0, match.start()) + 1)
        relative = path.relative_to(root.resolve())
        for number in sorted(line_numbers):
            findings.append(f"OpenAI-style key in tracked content: {relative}:{number}")
    return findings


def self_test():
    """Prove a key-shaped string fails, and that harmless strings do not."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        leaked = root / "committed.env"
        for label, secret in (
            ("project", project_key()),
            ("legacy", legacy_key()),
        ):
            leaked.write_text(f"OPENAI_API_KEY={secret}\n")
            findings = scan(root)
            if not findings:
                print(
                    f"self-test: {label} fixture key was not rejected", file=sys.stderr
                )
                return 1
            report = "\n".join(findings)
            if secret in report:
                print("self-test: report included the key", file=sys.stderr)
                return 1
        leaked.write_text(
            "\n".join(
                [
                    "OPENAI_API_KEY=",
                    "STRIPE_SECRET_KEY=sk_test_" + ("a" * 24),
                    'SECRET="sk-test-not-a-real-key"',
                    "https://api.openai.com/v1/chat/completions",
                ]
            )
            + "\n"
        )
        if scan(root):
            print("self-test: harmless strings were rejected", file=sys.stderr)
            return 1
    print("self-test: a key-shaped OpenAI string in a temporary file was rejected")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        help="Directory to scan. Defaults to the git toplevel.",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Reject a temporary key-shaped fixture, then exit.",
    )
    args = parser.parse_args(argv)
    if args.self_test:
        if args.root is not None:
            print("--self-test does not take --root", file=sys.stderr)
            return 2
        return self_test()
    root = args.root
    if root is None:
        root = _git_toplevel(Path.cwd())
        if root is None:
            print("not a git repository", file=sys.stderr)
            return 2
    findings = scan(root)
    if findings:
        for finding in findings:
            print(finding, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
