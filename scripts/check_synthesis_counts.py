"""Assert that the aggregate counts in docs/research_synthesis.md derive from its tables.

The 9/4 process-error count in an earlier draft was typed by hand and disagreed with the
table it summarised.  This script recomputes the summary numbers from the structured rows
so the two cannot drift apart again.

Run: python scripts/check_synthesis_counts.py
"""

import pathlib
import re
import sys

DOC = pathlib.Path(__file__).resolve().parent.parent / "docs" / "research_synthesis.md"


def section(text, heading):
    """Body of one '## N. ...' section, up to the next '## '."""
    start = text.index(heading)
    nxt = text.find("\n## ", start + 1)
    return text[start : nxt if nxt != -1 else len(text)]


def rows(body):
    """Numbered markdown table rows: those whose first cell is an integer."""
    out = []
    for line in body.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and re.fullmatch(r"\d+", cells[0]):
            out.append(cells)
    return out


def check(label, got, want):
    ok = got == want
    print(f"  [{'ok' if ok else 'FAIL'}] {label}: table={got} prose={want}")
    return ok


def main():
    text = DOC.read_text(encoding="utf-8")
    ok = True

    # -- Section 10: process-failure audit ------------------------------------
    body = section(text, "## 10. Research-process failure audit")
    table = rows(body)
    caught = [r[3] for r in table]

    unknown = [c for c in caught if not c.startswith(("BEFORE", "AFTER"))]
    if unknown:
        print(f"  [FAIL] unrecognised 'caught' values: {unknown}")
        ok = False

    n_total = len(table)
    n_before = sum(c.startswith("BEFORE") for c in caught)
    n_after = sum(c.startswith("AFTER") for c in caught)

    ids = [int(r[0]) for r in table]
    if ids != list(range(1, n_total + 1)):
        print(f"  [FAIL] process-error rows are not 1..N contiguous: {ids}")
        ok = False

    # The prose sentence these must match.
    m = re.search(
        r"(\w+) process errors were found across \d+ commits\.\s*\*\*(\w+)\*\* were caught"
        r" before.*?\*\*(\w+)\*\* were caught\s*> only afterwards",
        body,
        re.S,
    )
    if not m:
        m = re.search(
            r"(\w+) process errors were found.*?\*\*(\w+)\*\* were caught before"
            r".*?\*\*(\w+)\*\* were caught",
            body,
            re.S,
        )
    if not m:
        print("  [FAIL] could not locate the process-error summary sentence")
        return 1

    words = {
        "Thirteen": 13, "thirteen": 13,
        "Six": 6, "six": 6,
        "Seven": 7, "seven": 7,
    }
    try:
        prose = [words[g] for g in m.groups()]
    except KeyError as e:
        print(f"  [FAIL] unmapped number word in summary sentence: {e}")
        return 1

    ok &= check("process errors, total", n_total, prose[0])
    ok &= check("caught BEFORE outcomes", n_before, prose[1])
    ok &= check("caught AFTER outcomes", n_after, prose[2])

    if n_before + n_after != n_total:
        print(f"  [FAIL] {n_before} + {n_after} != {n_total}")
        ok = False

    # -- Section 3.6: mechanism dispositions ----------------------------------
    body = section(text, "## 3. Strongest quantitative findings")
    mech = [r for r in rows(body) if r[0].isdigit() and len(r) >= 6]
    mech = [r for r in mech if r[1].startswith("M") or r[5]]
    disp = [r[-1] for r in rows(body) if r[0].startswith("M")]
    # Rows in 3.6 are keyed M1..M8 in the first cell, so re-extract on that.
    disp = []
    for line in body.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and re.fullmatch(r"M\d+", cells[0]):
            disp.append(cells[-1])

    n_mech = len(disp)
    if n_mech != 8:  # M1..M7 tested on real data, M8 exploratory-only
        print(f"  [FAIL] expected 8 mechanism rows (M1-M8), found {n_mech}")
        ok = False

    # The denominator that matters: mechanisms carrying a numeric pass/fail gate.
    gated = [d for r, d in zip(
        [c for c in (
            [c.strip() for c in ln.strip().strip("|").split("|")]
            for ln in body.splitlines() if ln.startswith("|")
        ) if c and re.fullmatch(r"M\d+", c[0])], disp)
        if r[3].startswith("Yes")]
    ok &= check("gated mechanisms", len(gated), 5)
    ok &= check("gated failures", sum("FAIL" in d for d in gated), 3)
    ok &= check("gated passes", sum(d.startswith("**PASS") for d in gated), 1)
    ok &= check("gated accepted-but-underpowered",
                sum("UNDERPOWERED" in d for d in gated), 1)

    # Withdrawn formulations may appear only as quoted history, never asserted.
    unquoted = re.compile(
        r'(?<!["\u201c])\b(four of five|four (?:of them )?failed|sole survivor)\b',
        re.I)
    for n, line in enumerate(text.splitlines(), 1):
        stripped = re.sub(r'["\u201c\u201d][^"\u201c\u201d]*["\u201c\u201d]', "", line)
        if unquoted.search(stripped):
            print(f"  [FAIL] withdrawn phrase asserted unquoted at line {n}: "
                  f"{line[:90]}")
            ok = False

    print("\nOK" if ok else "\nFAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
