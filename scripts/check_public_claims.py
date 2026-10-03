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
from public_claim_ledger import FORBIDDEN, CANONICAL, RULE_IDENTITIES

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


# R3's reading was narrowed on 2026-10-02, not withdrawn: the within-slice residual stays
# positive (+5.8 pp, p = 0.26) and in the predicted direction, so what shrank is the size of the
# claim, not its sign. "Withdrawn" overstates the correction in the opposite direction from the
# original overclaim, which is still a wrong claim about the evidence.
#
# It was also a lint hole, which is why this is enforced rather than left to prose discipline:
# "withdrawn" sits in ALWAYS_EXEMPT, so any line that said R3 was withdrawn exempted itself from
# every other check on that line. Four such lines shipped. The exemption no longer applies to
# R3 lines, and the word is a violation on them.
R3_LINE = re.compile(r"\bR3\b|evidence[- ]gap", re.I)
WITHDRAW_WORD = re.compile(r"\bwithdraw(?:n|s|al|ing)?\b|\bwithdrew\b", re.I)
# "narrowed, not withdrawn" and "narrowed rather than withdrawn" are the correct phrasings and
# say the word in order to deny it. Only an un-negated use is the violation.
NEGATED_WITHDRAW = re.compile(
    r"\b(?:not|never|rather than|instead of|isn't|is not|wasn't|was not)\s+"
    r"(?:\*{0,2})withdraw", re.I)


def _r3_says_withdrawn(line: str) -> bool:
    if not (R3_LINE.search(line) and WITHDRAW_WORD.search(line)):
        return False
    return not NEGATED_WITHDRAW.search(line)


def _line_is_exempt(line: str, is_synthesis: bool = False) -> bool:
    low = line.lower()
    stripped = line.strip()
    # A blockquote or a struck span may quote "R3 withdrawn" as history; that is the repo's
    # correction convention and stays readable. Everything else may not.
    quoted_history = stripped.startswith(">") or "~~" in line
    if _r3_says_withdrawn(line) and not quoted_history:
        return False
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


def _check_r3_narrowed(path: pathlib.Path, lines: list[str]) -> list[dict]:
    """R3 lines must say 'narrowed', not 'withdrawn'. See the note above R3_LINE."""
    out = []
    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith(">") or "~~" in line:
            continue  # quoted history
        if not _r3_says_withdrawn(line):
            continue
        out.append({
            "file": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
            "line": lineno,
            "severity": "ERROR",
            "phrase": "R3 + withdraw",
            "message": (
                "R3's reading was NARROWED 2026-10-02, not withdrawn. The within-slice residual "
                "is +5.8 pp (p = 0.26) — positive, in the predicted direction, underpowered. The "
                "claim shrinks to unproven; it is not refuted, and the ACCEPTED disposition never "
                "moved. Use 'narrowed'. To quote the old wording as history, strike it (~~) or "
                "put it in a blockquote."
            ),
            "excerpt": stripped[:100],
        })
    return out


def _check_rule_identities(path: pathlib.Path, text: str) -> list[dict]:
    """A document that names a rule must also say what the rule fires on.

    Document-level, not line-level: the discriminator may appear in a table cell,
    a footnote, or three paragraphs away. The failure this catches is a document
    that describes R1 without ever mentioning `report_infeasible` — which is what
    writing from memory looks like, since a paraphrase keeps the label and drops
    the only token that identifies the rule.
    """
    # Collapse whitespace before matching. Prose wraps mid-phrase — JSX especially,
    # where "did the agent write / anything?" spans two source lines — and a
    # discriminator split across a newline is still a discriminator to a reader.
    low = re.sub(r"\s+", " ", text).lower()
    # "R1–R4" refers to the rules collectively and carries no obligation to
    # describe any one of them; only a document that singles a rule out has to
    # say what it fires on. Mask ranges before looking for individual names.
    searchable = re.sub(r"\bR\d\s*(?:[–\-—]|to|through)\s*R\d\b", " ", text, flags=re.I)

    violations = []
    for rule, ident in RULE_IDENTITIES.items():
        # Word-bounded so "R1" does not match "R10" or a hex string.
        if not re.search(rf"\b{re.escape(rule)}\b", searchable, re.I):
            continue
        if any(d.lower() in low for d in ident["discriminators"]):
            continue
        violations.append({
            "file": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
            "line": 0,
            "severity": "ERROR",
            "phrase": f"{rule} identity",
            "message": (
                f"Names {rule} but never says what it fires on. "
                f"{rule} is {ident['name']}: {ident['fires_on']}. "
                f"Expected one of {ident['discriminators']}. "
                f"Source: {ident['source']}."
            ),
        })
    return violations


def _check_file(path: pathlib.Path, is_synthesis: bool = False,
                include_warns: bool = False) -> list[dict]:
    if not path.exists():
        return [{"file": str(path), "line": 0, "severity": "WARN",
                 "phrase": "(missing)", "message": "File does not exist yet"}]

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    violations = _check_rule_identities(path, text)
    violations += _check_r3_narrowed(path, lines)

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
    parser.add_argument("--page", nargs="+", metavar="FILE", default=[],
                        help="Check an external page (e.g. portfolio .tsx components) for "
                             "rule-identity violations. All FILEs are concatenated and "
                             "checked as one document, since a page is one document to a "
                             "reader even when it is many files on disk.")
    args = parser.parse_args()

    all_violations = []

    if args.page:
        paths = [pathlib.Path(p).resolve() for p in args.page]
        missing = [p for p in paths if not p.exists()]
        if missing:
            print(f"ERROR: no such file: {missing[0]}")
            return 1
        joined = "\n".join(p.read_text(encoding="utf-8") for p in paths)
        all_violations.extend(_check_rule_identities(paths[0].parent, joined))

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
