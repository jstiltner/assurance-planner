"""Decision-procedure statistics.

A step runs one evidence source ``n`` times against a case and declares the case
FAILING when at least ``k`` of those runs flag it.  Given the source's measured
sensitivity and false-positive rate for this failure mode and population, the two
error probabilities of that procedure are exact binomial tails.

Only ``math`` is used.  No sampling, no optimisation library, no hidden constants.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from math import comb, sqrt

# Hard ceiling on enumerated replications.  Not a tuning parameter: it exists so an
# impossible error target terminates instead of looping.  A source that needs more
# than this many runs is reported as unable to meet the requirement.
MAX_REPLICATIONS = 64

#: Normal quantile for a two-sided 95% interval.  A v0 constant, not a ninth policy
#: knob: nothing in any scenario so far turns on the difference between 90% and 99%,
#: and adding the dial before anything needs it would be the kind of unexercised
#: abstraction the last pass spent its time deleting.
Z_95 = 1.959963984540054


def wilson_interval(
    successes: int, trials: int, z: float = Z_95
) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion.

    Frequentist, closed-form, and correct at the boundaries -- which is the whole
    reason for preferring it here.  The obvious alternative, the normal approximation
    ``p +- z*sqrt(p(1-p)/n)``, returns the degenerate interval ``[1.0, 1.0]`` for a
    deterministic oracle measured 30 times out of 30, which would let the planner
    claim certainty it has not bought.  Wilson returns ``[0.885, 1.0]`` for the same
    data, which is the honest statement.

    ``trials == 0`` returns the whole unit interval: no observations, no information.
    """
    if trials <= 0:
        return (0.0, 1.0)
    p = successes / trials
    denominator = 1.0 + z * z / trials
    centre = (p + z * z / (2.0 * trials)) / denominator
    half_width = (
        z * sqrt(p * (1.0 - p) / trials + z * z / (4.0 * trials * trials))
    ) / denominator
    return (max(0.0, centre - half_width), min(1.0, centre + half_width))


def _binomial_pmf(n: int, p: float, i: int) -> float:
    return comb(n, i) * (p**i) * ((1.0 - p) ** (n - i))


def prob_fewer_than(n: int, p: float, k: int) -> float:
    """P(Binomial(n, p) < k)."""
    return sum(_binomial_pmf(n, p, i) for i in range(0, min(k, n + 1)))


def prob_at_least(n: int, p: float, k: int) -> float:
    """P(Binomial(n, p) >= k)."""
    return sum(_binomial_pmf(n, p, i) for i in range(k, n + 1))


@dataclass(frozen=True, slots=True)
class DecisionProcedure:
    """``replications`` runs, fail the case at ``threshold_k`` flags."""

    replications: int
    threshold_k: int
    miss_probability: float
    false_alarm_probability: float

    @property
    def escalation_band(self) -> tuple[int, int] | None:
        """Flag counts that are evidence but do not meet the fail threshold.

        Empty for a single-run deterministic check, which is why a deterministic
        verification path does not acquire an escalation hop it does not need.
        """
        if self.threshold_k <= 1:
            return None
        return (1, self.threshold_k - 1)

    def describe(self) -> str:
        band = self.escalation_band
        band_txt = "none" if band is None else f"{band[0]}-{band[1]} flags"
        return (
            f"{self.replications} run(s), fail at >={self.threshold_k} flags "
            f"(P(miss)={self.miss_probability:.2e}, "
            f"P(false alarm)={self.false_alarm_probability:.2e}, "
            f"escalation band: {band_txt})"
        )


def error_probabilities(
    replications: int, threshold_k: int, sensitivity: float, false_positive_rate: float
) -> tuple[float, float]:
    miss = prob_fewer_than(replications, sensitivity, threshold_k)
    false_alarm = prob_at_least(replications, false_positive_rate, threshold_k)
    return miss, false_alarm


def procedure_for(
    replications: int,
    sensitivity: float,
    false_positive_rate: float,
    max_error: float,
) -> DecisionProcedure | None:
    """Best threshold for a *fixed* replication count, or None if none qualifies.

    Used by the enumerator, which proposes replication counts itself so that the
    chosen count is the outcome of ranking rather than of a solver's preference.
    """
    for k in range(1, replications + 1):
        miss, false_alarm = error_probabilities(
            replications, k, sensitivity, false_positive_rate
        )
        if miss <= max_error and false_alarm <= max_error:
            return DecisionProcedure(replications, k, miss, false_alarm)
    return None


@lru_cache(maxsize=4096)
def minimal_procedure(
    sensitivity: float, false_positive_rate: float, max_error: float
) -> DecisionProcedure | None:
    """Fewest replications meeting the error bound in both directions.

    Weakly monotone: decreasing in ``sensitivity``, increasing in
    ``false_positive_rate``.  ``tests/test_transitions.py`` asserts this over a grid
    rather than trusting the claim.
    """
    for n in range(1, MAX_REPLICATIONS + 1):
        procedure = procedure_for(n, sensitivity, false_positive_rate, max_error)
        if procedure is not None:
            return procedure
    return None
