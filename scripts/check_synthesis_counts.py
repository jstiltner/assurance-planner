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

    # The origin axis, added 2026-10-02.  The internal 13/6/7 and the external 11 are asserted
    # separately and never as a 24/6/18 triple: pooling them reads as though the project's own
    # audit had grown, which it did not, and the paper quotes 13/6/7.  See the second counting
    # rule in the section itself.
    origin = [r[4] for r in table]
    bad = sorted({o for o in origin if o not in ("internal", "external")})
    if bad:
        print(f"  [FAIL] unrecognised 'origin' values: {bad}")
        ok = False

    n_total = len(table)
    internal = [c for c, o in zip(caught, origin) if o == "internal"]
    external = [c for c, o in zip(caught, origin) if o == "external"]

    ids = [int(r[0]) for r in table]
    if ids != list(range(1, n_total + 1)):
        print(f"  [FAIL] process-error rows are not 1..N contiguous: {ids}")
        ok = False

    # The internal triple.  Anchored on "found by this project's own safeguards" so neither the
    # partly-superseded blockquote above it -- kept visible as history, per the repo's correction
    # convention -- nor the external paragraph below it can be picked up as this claim.
    m = re.search(
        r"\*\*Internal: (\d+) process errors\*\* found by this project's own safeguards"
        r".*?\*\*(\d+)\*\* were caught before"
        r".*?\*\*(\d+)\*\* were caught",
        body,
        re.S,
    )
    if not m:
        print("  [FAIL] could not locate the internal process-error summary sentence")
        return 1
    prose = [int(g) for g in m.groups()]

    ok &= check("internal process errors", len(internal), prose[0])
    ok &= check("internal caught BEFORE outcomes",
                sum(c.startswith("BEFORE") for c in internal), prose[1])
    ok &= check("internal caught AFTER outcomes",
                sum(c.startswith("AFTER") for c in internal), prose[2])

    m = re.search(r"\*\*External: (\d+) process errors\*\* found by an independent", body, re.S)
    if not m:
        print("  [FAIL] could not locate the external process-error summary sentence")
        return 1
    ok &= check("external process errors", len(external), int(m.group(1)))

    # All eleven external findings were made by reading already-published output, so AFTER is
    # structural, not incidental.  A future external row marked BEFORE would be a category error.
    n_ext_before = sum(c.startswith("BEFORE") for c in external)
    if n_ext_before:
        print(f"  [FAIL] {n_ext_before} external rows marked BEFORE; external findings are "
              "made on published output and are AFTER by construction")
        ok = False

    if len(internal) + len(external) != n_total:
        print(f"  [FAIL] {len(internal)} + {len(external)} != {n_total}")
        ok = False

    # The sum may be stated, but not alone.  Any paragraph giving 24 as a process-error count has
    # to carry the 13 + 11 breakdown, which is the correction this check exists to hold.
    #
    # Three things were extended on 2026-10-02 after the first version of this guard shipped and
    # missed the §18 abstract:
    #
    #   1. It ran over §10's body only.  The sentence that actually reached a reader was in the
    #      abstract, four sections away.  It now runs over the whole document.
    #   2. It matched digits only, and the abstract spelled the number: "Twenty-four process
    #      errors ... 18 of them caught only after".
    #   3. It skipped blockquote paragraphs wholesale.  The abstract *is* a blockquote -- the
    #      convention is that `>` marks a quotable draft, not that it marks history.  Only struck
    #      (~~) and quoted spans are exempt now, which is what the convention actually licenses.
    #
    # Checked per paragraph, not per line, because markdown wrapping puts a count and its
    # breakdown on different lines.  Scoped to 24-adjacent-to-"process error" so that row ranges
    # ("rows 14-24") and unrelated 24s do not trip it.
    NUM_24 = r"(?:\b24\b|\btwenty[- ]four\b)"
    PROCESS_24 = re.compile(
        rf"{NUM_24}[^.]{{0,60}}process[- ]error|process[- ]error[^.]{{0,60}}{NUM_24}", re.I)
    # The pooled after-count. 18 = 7 internal + 11 external, and quoting it implies this project's
    # own audit caught eighteen late errors. There is no ledger key for it; there must be no prose
    # for it either.
    POOLED_18 = re.compile(r"\b(?:18|eighteen)\b[^.]{0,40}(?:caught\s+)?(?:only\s+)?after", re.I)
    for para in re.split(r"\n\s*\n", text):
        if para.lstrip().startswith("|"):
            continue  # the table itself
        # Strike-through and quoted spans are how this repo keeps a superseded wording readable.
        plain = re.sub(r"~~.*?~~", "", para, flags=re.S)
        plain = re.sub(r'["\u201c][^"\u201c\u201d]*["\u201d]', "", plain)
        if PROCESS_24.search(plain) and not re.search(
                r"\b(13|11|eleven|thirteen)\b", plain):
            print("  [FAIL] process-error total of 24 given without its 13 + 11 parts: "
                  f"{' '.join(para.split())[:110]}")
            ok = False
        if POOLED_18.search(plain):
            print("  [FAIL] pooled after-count (18) asserted; it merges 7 internal with 11 "
                  f"external findings: {' '.join(para.split())[:110]}")
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
    # Until 2026-10-02 this asserted 5 gated / 3 failures.  R1 and R4 were counted as gated
    # because the 3.6 table said "Yes" in the threshold column, but §7 of the repair
    # preregistration gives them a direction and no accept/reject bar.  The gated set is
    # {R2, R3, RC1}; R1 and R4 are directional and are counted separately below.
    ok &= check("gated mechanisms", len(gated), 3)
    ok &= check("gated failures", sum("FAIL" in d for d in gated), 1)
    ok &= check("gated passes", sum(d.startswith("**PASS") for d in gated), 1)
    ok &= check("gated accepted-but-underpowered",
                sum("UNDERPOWERED" in d for d in gated), 1)

    directional = [d for r, d in zip(
        [c for c in (
            [c.strip() for c in ln.strip().strip("|").split("|")]
            for ln in body.splitlines() if ln.startswith("|")
        ) if c and re.fullmatch(r"M\d+", c[0])], disp)
        if "directional only" in r[3]]
    ok &= check("directional-only mechanisms", len(directional), 2)

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
