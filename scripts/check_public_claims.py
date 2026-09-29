"""
Lint public-facing documents for forbidden phrases and superseded values.

Checks:
  docs/research_synthesis.md
  docs/FINDINGS.md
  README.md

Exit code 1 if any ERROR-level violation is found unquoted.

Usage:
    python scripts/check_public_claims.py [--warn-only]
"""

import argparse
import os
import pathlib
import re
import sys

# Force UTF-8 output on Windows to handle tau/unicode in doc text
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from public_claim_ledger import FORBIDDEN, CANONICAL

# Public-facing artifacts: linted strictly
PUBLIC_TARGETS = [
    ROOT / "docs" / "FINDINGS.md",
    ROOT / "README.md",
]
# Source-of-record: scan only for unexpected recurrence (info-only, no exit-1)
REFERENCE_TARGETS = [
    ROOT / "docs" / "research_synthesis.md",
]

# Contexts that may legitimately contain forbidden phrases (withdrawal notes, history sections)
# Lines that are always exempt even in public docs
ALWAYS_EXEMPT = [
    "~~",           # strikethrough markdown
    "forbidden",    # explicitly in "forbidden wording" column
    "do not",       # "do not say X"
    "never write",
    "overclaim",
    "withdrawn",
    "superseded",
    "collided",
]

# Lines exempt only in the source-of-record (synthesis), not in public docs
SYNTHESIS_ONLY_EXEMPT = [
    "corrected",
    "earlier draft",
    "previously",
    "does not exist",
    "not exist",
    "no such",
    "history",
    "correction",
    "audit",
    "remove from",  # "REMOVE FROM PUBLIC-FACING CLAIMS" section
    "→",            # value correction arrows like "1.090× → 1.165×"
    "rejected",
    "wrong",
    "violated",
    "| d.",         # table row starting with | D.
    "class d",
    "oracle-only",
    "leakage",
]


def _line_is_exempt(line: str, is_synthesis: bool = False) -> bool:
    low = line.lower()
    stripped = line.strip()
    if stripped.startswith(">"):
        return True  # blockquote: historical/correction citation
    for marker in ALWAYS_EXEMPT:
        if marker in low:
            return True
    if is_synthesis:
        for marker in SYNTHESIS_ONLY_EXEMPT:
            if marker in low:
                return True
    return False


def _check_file(path: pathlib.Path, is_synthesis: bool = False,
                include_warns: bool = False) -> list[dict]:
    if not path.exists():
        return [{"file": str(path), "line": 0, "severity": "WARN",
                 "phrase": "(missing)", "message": "File does not exist yet"}]

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    violations = []

    for pattern, reason, severity in FORBIDDEN:
        if is_synthesis:
            # Synthesis is the correction record; only flag outright unguarded assertions
            if severity != "ERROR":
                continue
        else:
            if not include_warns and severity == "WARN":
                continue

        regex = re.compile(pattern, re.I)
        for lineno, line in enumerate(lines, 1):
            if not regex.search(line):
                continue
            if _line_is_exempt(line, is_synthesis=is_synthesis):
                continue
            violations.append({
                "file": str(path.relative_to(ROOT)),
                "line": lineno,
                "severity": "INFO" if is_synthesis else severity,
                "phrase": pattern,
                "message": reason,
                "excerpt": line.strip()[:100],
            })

    # Superseded numeric literals — only strict-check in public docs (not synthesis)
    if not is_synthesis:
        numeric_checks = [
            (r"\b37\.5%", "Collided τ-bench base rate (37.5%). Corrected to 40.3%."),
            (r"\b1\.090×?", "Collided τ-bench traj lift (1.090×). Corrected to 1.165×."),
            (r"\b0\.902×?", "Collided τ-bench task lift (0.902×). Corrected to 0.906×."),
            (r"\b59\.1%", "Collided τ-bench harm rate (59.1%). Corrected to 53.1%."),
            (r"net\s*[-−]\s*91\b", "Collided τ-bench veto net (−91). Corrected to −31."),
            (r"\b55\.6%", "Collided τ-bench figure (55.6%). Corrected to 83.3%."),
            (r"\b7\.189×?", "Withdrawn: invalid cross-variable comparison."),
        ]
        for pattern, reason in numeric_checks:
            regex = re.compile(pattern, re.I)
            for lineno, line in enumerate(lines, 1):
                if not regex.search(line):
                    continue
                if _line_is_exempt(line, is_synthesis=False):
                    continue
                violations.append({
                    "file": str(path.relative_to(ROOT)),
                    "line": lineno,
                    "severity": "ERROR",
                    "phrase": pattern,
                    "message": reason,
                    "excerpt": line.strip()[:100],
                })

    return violations


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--warn-only", action="store_true",
                        help="Also report WARN-level items")
    args = parser.parse_args()

    all_violations = []
    for path in PUBLIC_TARGETS:
        vios = _check_file(path, is_synthesis=False, include_warns=args.warn_only)
        all_violations.extend(vios)
    for path in REFERENCE_TARGETS:
        vios = _check_file(path, is_synthesis=True, include_warns=False)
        all_violations.extend(vios)

    errors = [v for v in all_violations if v["severity"] == "ERROR"]
    infos  = [v for v in all_violations if v["severity"] == "INFO"]
    warns  = [v for v in all_violations if v["severity"] == "WARN"]

    if errors or warns:
        for v in sorted(all_violations,
                        key=lambda x: (x["severity"] != "ERROR", x["file"], x["line"])):
            if v["severity"] == "INFO":
                continue  # synthesis info — print separately
            tag = f"[{v['severity']}]"
            print(f"{tag} {v['file']}:{v['line']}  pattern={v['phrase']!r}")
            print(f"       {v['message']}")
            if "excerpt" in v:
                print(f"       >>> {v['excerpt']}")
            print()

    if infos:
        print(f"  (synthesis reference hits — INFO only, not blocking: {len(infos)})")

    if not errors and not warns:
        if not any(p.exists() for p in PUBLIC_TARGETS):
            print("NOTE: public targets (README, FINDINGS) not yet created")
        else:
            print("OK — no violations in public documents")

    print(f"{len(errors)} error(s), {len(warns)} warning(s), {len(infos)} info(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
