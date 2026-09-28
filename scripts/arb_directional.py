"""Phase 3: split the primary's errors by direction before asking what fixes them.

Phase 2 reported ``P(alternate correct | primary wrong)`` on all of the primary's
errors at once.  That denominator mixes two different interventions.  Exonerating a
trajectory the primary falsely rejected is review-burden work; detecting a failure the
primary waved through is the assurance problem the project exists for.  A single rate
over both is dominated by whichever stratum is larger, and here the larger stratum is
the one the project cares less about.

So this script computes nothing new about the corpus.  It re-tabulates the *same*
paired verdicts into the eight cells of ``reference x primary x alternate``, which is
the complete sufficient statistic for every quantity below, and then reads the
directional numbers off it.  Two consequences of that choice are worth stating:

  - every rate here is a ratio of two cells, so the reader can recompute any of them
    from ``data/REAL_arb_directional.csv`` without rerunning anything.
  - the cells make the *operational* quantities visible, which the pooled rate hides.
    Under ``primary FAIL -> alternate adjudicates`` the only cases that move are the
    ones the primary called failure: the alternate exonerates some real successes
    (good) and some real failures (bad).  Those are two separate cells, and their
    difference is the whole value of that architecture.

Tier discipline.  ``functional -> aer`` was predeclared in
``docs/agent_reward_bench_gate1.md`` before any joint error table existed and is the
only confirmatory pair here.  The other seven are exploratory diagnostics.  The tier
rides in the output on every row so that a copied table cannot lose it.

Usage:
    python scripts/arb_import.py --tier-c    # writes the seven exploratory pairs
    python scripts/arb_directional.py        # reads them, writes the cell table
"""

import csv
import os
import sys
import tempfile
from math import sqrt

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
WORKDIR = os.environ.get("ARB_WORKDIR") or tempfile.gettempdir()
sys.path.insert(0, os.path.join(REPO, "src"))

from assurance_planner.complementarity import (  # noqa: E402
    POINT_ESTIMATE_FLOOR,
    Conditional,
    paired_errors,
)
from assurance_planner.loader import load_characterization  # noqa: E402

PRIMARY = "functional"

#: (alternate judge key, tier).  Every one of these pairs a programmatic verifier
#: against an LLM judge, which is why all eight were rated HIGH independence in Gate 1;
#: the tier column records which one was named in advance.
ALTERNATES = [
    ("aer",                           "A-CONFIRMATORY"),
    ("claude-3.7-sonnet-noscreen",    "C-EXPLORATORY"),
    ("gpt-4o-mini-noscreen",          "C-EXPLORATORY"),
    ("gpt-4o-mini-noscreen-noaxtree", "C-EXPLORATORY"),
    ("gpt-4o-noscreen",               "C-EXPLORATORY"),
    ("llama-3.3-70b-noscreen",        "C-EXPLORATORY"),
    ("nnetnav",                       "C-EXPLORATORY"),
    ("qwen-2.5-vl-noscreen",          "C-EXPLORATORY"),
]

#: Pre-outcome structural features, copied from the Gate 1 provenance table.  These are
#: the handles that were available *before* any error was scored, which is the only
#: thing that makes the section 5 comparison meaningful: a feature invented after
#: seeing phi would explain phi by construction.
STRUCTURE = {
    # judge: (prompt lineage, backbone, inputs, priced)
    "aer":                           ("AER",        "gpt-4o",            "axtree", True),
    "nnetnav":                       ("NNetNav",    "llama-3.3-70b",     "axtree", False),
    "claude-3.7-sonnet-noscreen":    ("simplified", "claude-3.7-sonnet", "axtree", True),
    "gpt-4o-noscreen":               ("simplified", "gpt-4o",            "axtree", True),
    "gpt-4o-mini-noscreen":          ("simplified", "gpt-4o-mini",       "axtree", True),
    "gpt-4o-mini-noscreen-noaxtree": ("simplified", "gpt-4o-mini",       "none",   True),
    "llama-3.3-70b-noscreen":        ("simplified", "llama-3.3-70b",     "axtree", False),
    "qwen-2.5-vl-noscreen":          ("simplified", "qwen-2.5-vl",       "axtree", False),
}

#: Success-class precision/recall as published in Table 7 of arXiv:2504.08942, in
#: upstream's polarity (positive class = success).  Used as a polarity check, not as a
#: target: if our failure-polarity table were inverted anywhere, specificity here would
#: come out as the complement of the published recall instead of matching it.
PUBLISHED_SUCCESS_PRECISION_RECALL = {
    "functional":                    (83.8, 55.9),
    "aer":                           (67.7, 71.9),
    "nnetnav":                       (52.5, 82.4),
    "gpt-4o-noscreen":               (69.8, 83.1),
    "gpt-4o-mini-noscreen":          (61.5, 86.1),
    "claude-3.7-sonnet-noscreen":    (68.8, 81.6),
    "llama-3.3-70b-noscreen":        (67.7, 79.0),
    "qwen-2.5-vl-noscreen":          (64.3, 89.8),
}

#: The other predeclared pair.  Analysed separately and last, because it answers a
#: different question: every result above is conditioned on a primary whose errors are
#: 80% false alarms, and nothing in the eight-pair table can say whether that mix is a
#: property of evaluator pairing or a property of this one primary's operating point.
TIER_B = ("aer", "nnetnav", "B-CONFIRMATORY")


def run_path(alternate, primary=PRIMARY):
    name = f"REAL_arb_{primary}_x_{alternate}.yaml"
    committed = os.path.join(REPO, "data", name)
    return committed if os.path.exists(committed) else os.path.join(WORKDIR, name)


class Cells:
    """The eight-cell table of reference x primary x alternate, and nothing else.

    Named for what each cell *means operationally* rather than for its coordinates,
    because the whole point of the split is that ``primary_only_detects`` and
    ``primary_false_alarm_only`` are the same coordinate pattern with opposite value.
    """

    FIELDS = (
        "both_detect",                 # ref fail, both say fail
        "primary_only_detects",        # ref fail, primary fail, alternate pass
        "alternate_only_detects",      # ref fail, primary pass, alternate fail
        "both_miss",                   # ref fail, both say pass
        "both_false_alarm",            # ref pass, both say fail
        "primary_false_alarm_only",    # ref pass, primary fail, alternate pass
        "alternate_false_alarm_only",  # ref pass, primary pass, alternate fail
        "both_clear",                  # ref pass, both say pass
    )

    def __init__(self):
        for f in self.FIELDS:
            setattr(self, f, 0)

    def add(self, reference, primary, alternate):
        if reference:
            if primary and alternate:      self.both_detect += 1
            elif primary:                  self.primary_only_detects += 1
            elif alternate:                self.alternate_only_detects += 1
            else:                          self.both_miss += 1
        else:
            if primary and alternate:      self.both_false_alarm += 1
            elif primary:                  self.primary_false_alarm_only += 1
            elif alternate:                self.alternate_false_alarm_only += 1
            else:                          self.both_clear += 1

    @property
    def total(self):
        return sum(getattr(self, f) for f in self.FIELDS)

    # --- marginal confusion matrices, both on this pair's paired subset -------------

    @property
    def primary(self):
        """(TP, FN, FP, TN) for the primary.  Failure is the positive class."""
        return (
            self.both_detect + self.primary_only_detects,
            self.alternate_only_detects + self.both_miss,
            self.both_false_alarm + self.primary_false_alarm_only,
            self.alternate_false_alarm_only + self.both_clear,
        )

    @property
    def alternate(self):
        return (
            self.both_detect + self.alternate_only_detects,
            self.primary_only_detects + self.both_miss,
            self.both_false_alarm + self.alternate_false_alarm_only,
            self.primary_false_alarm_only + self.both_clear,
        )

    # --- the two directional quantities, kept apart --------------------------------

    @property
    def missed_failure_catch(self):
        """Of the failures the primary let through, how many does the alternate see?

        The assurance quantity.  Its denominator is the primary's false negatives,
        which in this corpus is the small stratum, and small is the point: no amount of
        aggregate support substitutes for support *here*.
        """
        return Conditional(
            "P(alternate correct | primary false negative)",
            self.alternate_only_detects,
            self.alternate_only_detects + self.both_miss,
        )

    @property
    def false_alarm_rescue(self):
        """Of the successes the primary rejected, how many does the alternate clear?

        A review-burden quantity.  It becomes an assurance quantity only under a
        declared scenario in which a false rejection carries comparable consequence,
        and no such scenario is declared here.
        """
        return Conditional(
            "P(alternate correct | primary false positive)",
            self.primary_false_alarm_only,
            self.both_false_alarm + self.primary_false_alarm_only,
        )

    # --- what each candidate architecture would actually do ------------------------

    @property
    def adjudication_balance(self):
        """``primary FAIL -> alternate adjudicates``: cases cleared, right and wrong.

        Only cases the primary called failure are touched.  Of those the alternate
        overturns some real successes (a correction) and some real failures (a new
        missed failure).  Reported as a pair, never netted into one number: the two
        errors are not interchangeable and netting them assumes the exchange rate that
        the project refuses to assume.
        """
        return self.primary_false_alarm_only, self.primary_only_detects

    @property
    def escalation_balance(self):
        """``primary PASS -> alternate escalates``: failures caught, alarms added."""
        return self.alternate_only_detects, self.alternate_false_alarm_only

    # --- the same question conditioned only on what a running system can see -------

    @property
    def overturn_to_pass_precision(self):
        """P(reference = pass | primary said fail, alternate said pass).

        The directional rates above condition on the reference label, which a running
        system does not have: ``false_alarm_rescue`` answers "given this was a false
        alarm, does the alternate clear it", and nothing selects the false alarms at
        runtime.  This conditions only on the two verdicts, which are observable, and
        so it is the rate that an adjudication policy would actually operate at.  The
        two differ by a lot whenever the primary's positive class is mostly correct.
        """
        right, wrong = self.primary_false_alarm_only, self.primary_only_detects
        return Conditional(
            "P(alternate correct | primary FAIL, alternate PASS)", right, right + wrong
        )

    @property
    def overturn_to_fail_precision(self):
        """P(reference = fail | primary said pass, alternate said fail)."""
        right, wrong = self.alternate_only_detects, self.alternate_false_alarm_only
        return Conditional(
            "P(alternate correct | primary PASS, alternate FAIL)", right, right + wrong
        )

    # --- paired superiority, as an interval rather than a test ---------------------

    @property
    def failure_side_discordance(self):
        """Among failure-labelled cases, who is right where the two disagree.

        ``Conditional`` over the discordant cells only: successes are cases where the
        alternate is the one that is right.  An interval clear of 0.5 is paired
        evidence that one source is better on this stratum; an interval containing 0.5
        is not, however far apart the two marginal rates look.  This is the conditional
        proportion McNemar's test is a test of, reported as an interval because the
        project reports intervals and because a p-value would invite a threshold that
        has not been declared.
        """
        a, b = self.alternate_only_detects, self.primary_only_detects
        return Conditional("alternate right | disagreement on a failure", a, a + b)

    @property
    def success_side_discordance(self):
        a, b = self.primary_false_alarm_only, self.alternate_false_alarm_only
        return Conditional("alternate right | disagreement on a success", a, a + b)


def rate(successes, trials):
    return Conditional("", successes, trials)


def fmt(cond, places=3):
    """Point estimate with its Wilson interval, and a marker when the n is thin."""
    if cond.trials == 0:
        return "n/a (n=0)"
    low, high = cond.interval
    mark = " THIN" if cond.thin_denominator else ""
    return f"{cond.point:.{places}f} [{low:.{places}f}, {high:.{places}f}] n={cond.trials}{mark}"


def phi(cells):
    """Pearson phi for (primary wrong) x (alternate wrong), folded from the eight cells.

    Same quantity ``PairedErrors.error_association_phi`` reports; recomputed here only
    to prove the eight-cell table folds back to the four-cell one, which
    ``check_against_repo_machinery`` asserts.
    """
    a = cells.both_miss + cells.both_false_alarm
    b = cells.primary_false_alarm_only + cells.alternate_only_detects
    c = cells.primary_only_detects + cells.alternate_false_alarm_only
    d = cells.both_detect + cells.both_clear
    denominator = (a + b) * (c + d) * (a + c) * (b + d)
    if denominator == 0:
        return None
    return (a * d - b * c) / sqrt(denominator)


def load_pair(alternate, primary=PRIMARY):
    """Return (cells, per-slice cells, alternate costs, unpaired count, run, verdicts)."""
    run = load_characterization(run_path(alternate, primary))
    cells, by_slice, costs, unpaired, verdicts = Cells(), {}, [], 0, {}
    for case in run.cases:
        if len(case.outcomes) != 1:
            raise ValueError(f"{alternate}: expected single-shot, got {len(case.outcomes)}")
        if not case.alternate_outcomes:
            unpaired += 1
            continue
        primary, alt = case.outcomes[0], case.alternate_outcomes[0]
        cells.add(case.reference_label, primary, alt)
        by_slice.setdefault(case.slice_id, Cells()).add(case.reference_label, primary, alt)
        costs.extend(case.alternate_costs_usd)
        verdicts[case.case_id] = alt
    return cells, by_slice, costs, unpaired, run, verdicts


def check_against_repo_machinery(alternate, cells):
    """The hand-rolled cells must agree with ``paired_errors`` on the pooled figures.

    Cheap, and it is the only thing standing between a re-tabulation bug and a report
    full of confident directional numbers that do not add up to the published pooled
    ones.
    """
    run = load_characterization(run_path(alternate))
    table = paired_errors(run.cases)
    pooled = rate(
        cells.primary_false_alarm_only + cells.alternate_only_detects,
        cells.primary[1] + cells.primary[2],
    )
    reference = table.alternate_correct_given_primary_wrong
    assert (pooled.successes, pooled.trials) == (reference.successes, reference.trials), (
        f"{alternate}: re-tabulation disagrees with paired_errors "
        f"({pooled.successes}/{pooled.trials} vs {reference.successes}/{reference.trials})"
    )
    assert abs(phi(cells) - table.error_association_phi) < 1e-12, f"{alternate}: phi drift"
    return table


def polarity_check(name, tp, fn, fp, tn):
    """Recompute upstream's success-class precision/recall and compare to the paper.

    In our polarity the positive class is the failure, so upstream's success class is
    our negative one: their precision is our NPV, their recall is our specificity.  If
    any part of the import had inverted a label, these would land at the complements of
    the published values rather than at the values.

    An exact match is expected only for judges that parsed every case.  Where a judge
    has unparseable verdicts the figures diverge by construction and in a known
    direction: upstream scores an unparseable verdict as a wrong prediction, this
    project drops it, so our denominators are smaller.  Reported, not corrected.
    """
    published = PUBLISHED_SUCCESS_PRECISION_RECALL.get(name)
    if published is None:
        return None
    npv = tn / (tn + fn) if (tn + fn) else 0.0
    specificity = tn / (tn + fp) if (tn + fp) else 0.0
    return (published, (npv * 100.0, specificity * 100.0))


def consensus(missed, false_alarms, all_verdicts):
    """How many of the eight alternates rescue each of the primary's errors.

    The eight pair tables answer "how many of the 32 does this alternate catch" eight
    times over.  They cannot answer "how many of the 32 does *anything available*
    catch", because that requires joining on the case, and it is the version of the
    question that bounds the whole architecture: a case missed by a programmatic
    verifier and by eight LLM judges spanning five backbones and three prompt lineages
    is not going to be recovered by adding a ninth, and no amount of repeating any one
    of them will reach it either.

    The caveat that must travel with this: agreement across *judges* is not the same
    measurement as agreement across *repeats of one judge*.  This bounds what different
    evidence can do.  It says nothing about what repetition can do, which remains
    unmeasured everywhere in this corpus.
    """
    for label, cases, want in (
        ("MISSED FAILURES (reference fail, primary passed)", missed, True),
        ("FALSE ALARMS (reference pass, primary failed)", false_alarms, False),
    ):
        histogram, by_slice_zero = {}, {}
        for case_id, slice_id in cases.items():
            judged = [v[case_id] for v in all_verdicts.values() if case_id in v]
            correct = sum(1 for v in judged if v is want)
            histogram.setdefault((correct, len(judged)), []).append(slice_id)
            if correct == 0:
                by_slice_zero[slice_id] = by_slice_zero.get(slice_id, 0) + 1
        total = len(cases)
        unreachable = sum(len(v) for (c, _), v in histogram.items() if c == 0)
        print(f"CONSENSUS OVER THE PRIMARY'S {label}  n={total}")
        for (correct, judged), members in sorted(histogram.items()):
            print(f"  {correct}/{judged} alternates correct: {len(members):4d} cases "
                  f"({len(members) / total:5.1%})")
        print(f"  reachable by at least one of the eight: {total - unreachable}/{total} "
              f"({(total - unreachable) / total:.1%})")
        print(f"  missed by the primary and by every alternate: {unreachable}/{total} "
              f"({unreachable / total:.1%})  by slice: {dict(sorted(by_slice_zero.items()))}")
        print()


def structure_versus_measurement(rows):
    """Did any pre-outcome structural feature order the pairs the way phi did?

    Descriptive only, and on eight points.  The question is not "fit a model" -- eight
    points cannot support one -- but the much weaker one the Gate 1 predeclaration
    implicitly bet on: that choosing an alternate with a distinct prompt lineage and a
    distinct backbone would buy error diversity.  Printing the two orderings beside one
    another is enough to see whether that bet had any purchase.
    """
    def order(key):
        return [r["alternate"] for r in sorted(rows, key=key, reverse=True)]

    by_phi = order(lambda r: float(r["phi"]))
    by_sensitivity = order(
        lambda r: r["alternate_tp"] / (r["alternate_tp"] + r["alternate_fn"])
    )
    print("STRUCTURE VERSUS MEASURED ERROR ASSOCIATION")
    print(f"  {'alternate':32s} {'lineage':11s} {'backbone':18s} {'phi':>7s} "
          f"{'sens':>6s} {'catch':>7s} {'rescue':>7s}")
    for r in sorted(rows, key=lambda r: float(r["phi"]), reverse=True):
        sens = r["alternate_tp"] / (r["alternate_tp"] + r["alternate_fn"])
        catch = r["missed_failure_catch_num"] / r["missed_failure_catch_den"]
        rescue = r["false_alarm_rescue_num"] / r["false_alarm_rescue_den"]
        print(f"  {r['alternate']:32s} {r['prompt_lineage']:11s} {r['backbone']:18s} "
              f"{float(r['phi']):+7.3f} {sens:6.3f} {catch:7.3f} {rescue:7.3f}")
    agree = sum(1 for a, b in zip(by_phi, by_sensitivity) if a == b)
    print(f"  ordering by phi and ordering by the alternate's own failure-sensitivity "
          f"agree on {agree}/8 positions")
    print(f"    by phi:         {' > '.join(by_phi)}")
    print(f"    by sensitivity: {' > '.join(by_sensitivity)}")
    print()


def pareto(rows, primary_rates):
    """Does anything dominate anything else on the two error rates we actually measured?

    Replacement is checked before routing because a router built around a dominated
    default is an expensive way to reproduce a cheaper evaluator's answers.  The check
    is deliberately narrow: only false-negative and false-positive rate, because those
    are the two dimensions measured for every source here.  Cost is measured for five
    of the nine and structurally absent or unpriced for the rest, and latency is
    measured for none, so neither can enter a dominance test without inventing the
    missing values.  Dominance established here is therefore dominance *on error only*,
    which is a strictly weaker claim than operational dominance and is labelled as such
    wherever it is reported.
    """
    entries = [("PRIMARY " + PRIMARY, *primary_rates, "absent (no model call)")]
    for r in rows:
        fnr = r["alternate_fn"] / (r["alternate_tp"] + r["alternate_fn"])
        fpr = r["alternate_fp"] / (r["alternate_fp"] + r["alternate_tn"])
        cost = (f"${float(r['alternate_cost_usd_mean']):.4f}/judgment"
                if r["alternate_cost_usd_mean"] else r["alternate_cost_state"])
        entries.append((r["alternate"], fnr, fpr, cost))

    print("REPLACEMENT GATE -- Pareto dominance on measured error rates only")
    print(f"  {'source':34s} {'FNR':>6s} {'FPR':>6s}  cost")
    for name, fnr, fpr, cost in entries:
        print(f"  {name:34s} {fnr:6.3f} {fpr:6.3f}  {cost}")
    dominated = False
    for name, fnr, fpr, _ in entries:
        beaten = [
            other for other, ofnr, ofpr, _ in entries
            if other != name and ofnr <= fnr and ofpr <= fpr
            and (ofnr < fnr or ofpr < fpr)
        ]
        if beaten:
            dominated = True
            print(f"  {name} is dominated on both error rates by: {', '.join(beaten)}")
    if not dominated:
        print("  no source is dominated on both error rates")
    print()


def tier_b():
    """The same directional split with a mid-sensitivity primary instead of a maximal one.

    Not a ninth candidate and not comparable to the eight: different primary, different
    strata, different denominators.  It is here to answer one question the eight cannot
    -- whether ``the assurance stratum is tiny`` is a finding about evaluator pairing or
    an artifact of having predeclared the most trigger-happy verdict source available.
    """
    primary, alternate, tier = TIER_B
    cells, _, _, unpaired, run, _ = load_pair(alternate, primary)
    q_tp, q_fn, q_fp, q_tn = cells.primary
    a_tp, a_fn, a_fp, a_tn = cells.alternate
    cleared_right, cleared_wrong = cells.adjudication_balance
    caught, added = cells.escalation_balance
    print(f"{tier}  {primary} -> {alternate}   paired n={cells.total} "
          f"(dropped {unpaired})")
    print(f"  primary   TP={q_tp} FN={q_fn} FP={q_fp} TN={q_tn}  errors={q_fn + q_fp}")
    print(f"    error mix {q_fn} missed failures / {q_fp} false alarms "
          f"= {q_fp / (q_fn + q_fp):.1%} false alarms")
    print(f"  alternate TP={a_tp} FN={a_fn} FP={a_fp} TN={a_tn}  errors={a_fn + a_fp}")
    print(f"  MISSED-FAILURE CATCH  {fmt(cells.missed_failure_catch)}")
    print(f"  FALSE-ALARM RESCUE    {fmt(cells.false_alarm_rescue)}")
    print(f"  adjudicate on primary FAIL: clears {cleared_right} real successes, "
          f"clears {cleared_wrong} real failures")
    print(f"  escalate on primary PASS:   catches {caught} real failures, "
          f"adds {added} false alarms")
    print(f"  OVERTURN TO PASS precision {fmt(cells.overturn_to_pass_precision)}")
    print(f"  OVERTURN TO FAIL precision {fmt(cells.overturn_to_fail_precision)}")
    print(f"  phi {phi(cells):+.3f}")
    print()


def main():
    rows = []
    baseline_run = load_characterization(run_path("aer"))
    full_n = sum(1 for c in baseline_run.cases if c.outcomes)

    #: The primary's own confusion matrix on every case it decided, independent of any
    #: alternate.  Quoted separately because each pair below drops the cases where its
    #: alternate failed to parse, so no pair's primary column is the primary's own.
    base = Cells()
    for case in baseline_run.cases:
        base.add(case.reference_label, case.outcomes[0], case.outcomes[0])
    p_tp = base.both_detect
    p_fn = base.both_miss
    p_fp = base.both_false_alarm
    p_tn = base.both_clear

    print(f"PRIMARY BASELINE  {PRIMARY}  n={full_n}")
    print(f"  TP={p_tp} FN={p_fn} FP={p_fp} TN={p_tn}  errors={p_fn + p_fp}")
    print(f"  sensitivity  {fmt(rate(p_tp, p_tp + p_fn))}")
    print(f"  specificity  {fmt(rate(p_tn, p_tn + p_fp))}")
    print(f"  precision    {fmt(rate(p_tp, p_tp + p_fp))}")
    print(f"  FNR          {fmt(rate(p_fn, p_tp + p_fn))}")
    print(f"  FPR          {fmt(rate(p_fp, p_fp + p_tn))}")
    print(f"  error mix    {p_fn} missed failures / {p_fp} false alarms "
          f"= {p_fp / (p_fn + p_fp):.1%} false alarms")
    pub = polarity_check(PRIMARY, p_tp, p_fn, p_fp, p_tn)
    print(f"  polarity check: upstream success precision/recall published "
          f"{pub[0][0]:.1f}/{pub[0][1]:.1f}, recomputed {pub[1][0]:.1f}/{pub[1][1]:.1f}")
    print()

    #: Case ids of the primary's two error strata, so the eight alternates can be
    #: asked about the *same* cases rather than about eight separate denominators.
    missed = {c.case_id: c.slice_id for c in baseline_run.cases
              if c.reference_label and not c.outcomes[0]}
    false_alarms = {c.case_id: c.slice_id for c in baseline_run.cases
                    if not c.reference_label and c.outcomes[0]}
    all_verdicts = {}

    for alternate, tier in ALTERNATES:
        cells, by_slice, costs, unpaired, run, verdicts = load_pair(alternate)
        all_verdicts[alternate] = verdicts
        table = check_against_repo_machinery(alternate, cells)
        a_tp, a_fn, a_fp, a_tn = cells.alternate
        q_tp, q_fn, q_fp, q_tn = cells.primary
        lineage, backbone, inputs, priced = STRUCTURE[alternate]
        cleared_right, cleared_wrong = cells.adjudication_balance
        caught, added = cells.escalation_balance
        pub = polarity_check(alternate, a_tp, a_fn, a_fp, a_tn)

        row = {
            "tier": tier,
            "alternate": alternate,
            "alternate_version": str(run.alternate_version),
            "paired_support": cells.total,
            "unpaired_dropped": unpaired,
            "prompt_lineage": lineage,
            "backbone": backbone,
            "inputs": inputs,
            "primary_tp_in_pair": q_tp,
            "primary_fn_in_pair": q_fn,
            "primary_fp_in_pair": q_fp,
            "primary_tn_in_pair": q_tn,
            "alternate_tp": a_tp,
            "alternate_fn": a_fn,
            "alternate_fp": a_fp,
            "alternate_tn": a_tn,
            "missed_failure_catch_num": cells.missed_failure_catch.successes,
            "missed_failure_catch_den": cells.missed_failure_catch.trials,
            "false_alarm_rescue_num": cells.false_alarm_rescue.successes,
            "false_alarm_rescue_den": cells.false_alarm_rescue.trials,
            "adjudication_cleared_correctly": cleared_right,
            "adjudication_cleared_wrongly": cleared_wrong,
            "escalation_failures_caught": caught,
            "escalation_alarms_added": added,
            "overturn_to_pass_num": cells.overturn_to_pass_precision.successes,
            "overturn_to_pass_den": cells.overturn_to_pass_precision.trials,
            "overturn_to_fail_num": cells.overturn_to_fail_precision.successes,
            "overturn_to_fail_den": cells.overturn_to_fail_precision.trials,
            "phi": f"{phi(cells):.4f}" if phi(cells) is not None else "",
            "joint_error_num": table.both_wrong,
            "joint_error_den": table.decided,
            "verdict_disagreements": table.verdict_disagreements,
            "alternate_cost_observations": len(costs),
            "alternate_cost_usd_mean": f"{sum(costs) / len(costs):.6f}" if costs else "",
            "alternate_cost_state": (
                "measured" if costs else
                "unpriced-self-hosted (vllm records literal 0.0)" if not priced else
                "absent"
            ),
            "alternate_latency": "UNMEASURED (upstream records no judge timing)",
        }
        for f in Cells.FIELDS:
            row[f] = getattr(cells, f)
        rows.append(row)

        print(f"{tier}  {PRIMARY} -> {alternate}   paired n={cells.total} "
              f"(dropped {unpaired} with no alternate verdict)")
        print("  cells  " + "  ".join(f"{f}={getattr(cells, f)}" for f in Cells.FIELDS))
        print(f"  alternate  TP={a_tp} FN={a_fn} FP={a_fp} TN={a_tn} errors={a_fn + a_fp}")
        print(f"    sensitivity {fmt(rate(a_tp, a_tp + a_fn))}")
        print(f"    specificity {fmt(rate(a_tn, a_tn + a_fp))}")
        print(f"    precision   {fmt(rate(a_tp, a_tp + a_fp))}")
        print(f"    FNR         {fmt(rate(a_fn, a_tp + a_fn))}")
        print(f"    FPR         {fmt(rate(a_fp, a_fp + a_tn))}")
        print(f"  MISSED-FAILURE CATCH  {fmt(cells.missed_failure_catch)}")
        print(f"  FALSE-ALARM RESCUE    {fmt(cells.false_alarm_rescue)}")
        print(f"  pooled recovery       {fmt(table.alternate_correct_given_primary_wrong)}")
        print(f"  adjudicate on primary FAIL: clears {cleared_right} real successes, "
              f"clears {cleared_wrong} real failures")
        print(f"  escalate on primary PASS:   catches {caught} real failures, "
              f"adds {added} false alarms")
        print(f"  OVERTURN TO PASS precision {fmt(cells.overturn_to_pass_precision)}")
        print(f"  OVERTURN TO FAIL precision {fmt(cells.overturn_to_fail_precision)}")
        print(f"  failure-side discordance {fmt(cells.failure_side_discordance)}")
        print(f"  success-side discordance {fmt(cells.success_side_discordance)}")
        print(f"  phi {phi(cells):+.3f}  joint error {fmt(table.joint_error_rate)}  "
              f"disagreements {table.verdict_disagreements}")
        if pub:
            print(f"  polarity check: published {pub[0][0]:.1f}/{pub[0][1]:.1f}, "
                  f"recomputed {pub[1][0]:.1f}/{pub[1][1]:.1f}")
        print("  by slice (directional, support-gated):")
        for slice_id in sorted(by_slice):
            s = by_slice[slice_id]
            mfc, far = s.missed_failure_catch, s.false_alarm_rescue
            print(f"    {slice_id:18s} n={s.total:4d}  catch {fmt(mfc)}   rescue {fmt(far)}")
        print()

    pareto(rows, (p_fn / (p_tp + p_fn), p_fp / (p_fp + p_tn)))
    consensus(missed, false_alarms, all_verdicts)
    structure_versus_measurement(rows)
    tier_b()

    dest = os.path.join(REPO, "data", "REAL_arb_directional.csv")
    header = list(rows[0].keys())
    with open(dest, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {dest}")
    print(f"point-estimate floor for the THIN marker: {POINT_ESTIMATE_FLOOR}")


if __name__ == "__main__":
    main()
