"""assurance-plan <scenario.yaml> [--context NAME]

    assurance-plan characterize-evaluator <runs.yaml> [--max-error E]
    assurance-plan characterize-alternate <paired_runs.yaml> [--emit PATH]
    assurance-plan benchmark-policies <runs.yaml> [--folds K] [--judge-cost USD] ...
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .artifacts import load_artifact, write_artifact
from .benchmark import (
    allocation_diagnostic,
    compare,
    matched_control,
    fit_by_reference_label,
    marginal_value,
    sample_size_warnings,
    slice_diagnostics,
)
from .benchmark_report import render_benchmark
from .characterization import characterize
from .complementarity import analyse_complementarity
from .complementarity_report import render_complementarity
from .loader import load, load_characterization
from .planner import plan
from .policies import (
    AlternateCharacteristics,
    CostModel,
    UnqualifiedAlternateError,
    default_policies,
    stratified_folds,
)
from .rationale import render, render_characterization

SUBCOMMANDS = (
    "characterize-evaluator",
    "characterize-alternate",
    "benchmark-policies",
)


def _plan_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="assurance-plan")
    parser.add_argument("scenario", help="path to a scenario YAML file")
    parser.add_argument(
        "--context",
        action="append",
        default=None,
        help="context name to plan for; repeatable. Default: every context in the file",
    )
    parser.add_argument("--max-rejections", type=int, default=6)
    args = parser.parse_args(argv)

    scenario = load(args.scenario)
    names = args.context or [request.name for request in scenario.requests]

    exit_code = 0
    for index, name in enumerate(names):
        request = scenario.request(name)
        result = plan(
            request.context, scenario.failure_mode, request.profile, scenario.world
        )
        if index:
            print()
        print("=" * 78)
        print(f"{scenario.name} :: {name}")
        print("=" * 78)
        print(
            render(
                result,
                request.context,
                scenario.failure_mode,
                request.profile,
                scenario.world,
                max_rejections=args.max_rejections,
            )
        )
        if result.selected is None:
            exit_code = 2
    return exit_code


def _characterize_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="assurance-plan characterize-evaluator")
    parser.add_argument("runs", help="path to a per-case evaluator outcomes YAML file")
    parser.add_argument(
        "--max-error",
        type=float,
        default=0.05,
        help=(
            "the residual error a plan must bound, supplied as policy. This is the "
            "same number an AssuranceProfile carries; it is an input to the analysis, "
            "never inferred from the data. Default: 0.05"
        ),
    )
    parser.add_argument("--max-replications", type=int, default=12)
    args = parser.parse_args(argv)

    run = load_characterization(args.runs)
    analysis = characterize(run, args.max_error, args.max_replications)
    print("=" * 78)
    print(f"Evaluator characterization :: {run.evaluator_version}")
    print("=" * 78)
    print(render_characterization(analysis))
    #: Exit 1, not 0, when the data contradicts the model the planner is using.  A
    #: report nobody reads is worth less than a non-zero status in a pipeline.
    return 1 if analysis.independence_is_implausible else 0


def _alternate_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="assurance-plan characterize-alternate")
    parser.add_argument(
        "runs", help="a paired per-case outcomes YAML file (both sources, same cases)"
    )
    parser.add_argument("--max-error", type=float, default=0.05)
    parser.add_argument("--max-replications", type=int, default=12)
    parser.add_argument(
        "--break-even-recovery",
        type=float,
        metavar="R",
        default=None,
        help=(
            "the recovery rate at which escalating to the alternate begins to pay for "
            "itself, supplied as policy in the same way --max-error is. Set by "
            "consequence, prevalence, price and latency; never inferred from the data "
            "being analysed. There is deliberately no default: without it the report "
            "gives descriptive statistics and refuses to call any of them "
            "decision-sufficient"
        ),
    )
    parser.add_argument(
        "--emit",
        metavar="PATH",
        help=(
            "write an alternate qualification artifact. Refused when the run has no "
            "alternate observations, and marked synthetic when the run is"
        ),
    )
    args = parser.parse_args(argv)

    if args.break_even_recovery is not None and not 0.0 <= args.break_even_recovery <= 1.0:
        parser.error("--break-even-recovery must be a probability in [0, 1]")

    run = load_characterization(args.runs)
    analysis = analyse_complementarity(run, args.break_even_recovery)
    primary = characterize(run, args.max_error, args.max_replications)
    alternate_run = run.alternate_view() if run.alternate_version else None
    alternate = (
        characterize(alternate_run, args.max_error, args.max_replications)
        if alternate_run is not None and alternate_run.cases
        else None
    )

    print("=" * 78)
    print(f"Alternate source characterization :: {run.evaluator_version}")
    print("=" * 78)
    print(render_complementarity(analysis, primary, alternate))

    if args.emit:
        if alternate is None:
            parser.error(
                "cannot emit an alternate qualification artifact from a run with no "
                "paired alternate observations"
            )
        print(f"\nwrote {write_artifact(alternate, args.emit)}")

    #: 1 whenever the decision is unsupported, which at present is always.  A pipeline
    #: that treats 0 as "the alternate is fine" must not be able to get a 0 out of a
    #: study that measured nothing -- nor out of one that measured something and was
    #: never told what would count as success.
    return 0 if analysis.measured and analysis.decisive else 1


#: ``slots=True`` makes the dataclass class attributes descriptors rather than
#: values, so argparse defaults are read off an instance.
_DEFAULT_COST = CostModel()


def _alternate_characteristics(args) -> AlternateCharacteristics:
    """Neither flag given returns an unusable instance, on purpose.

    It does not raise here.  A benchmark of primary-only policies is a legitimate run
    that needs no alternate evidence, and refusing it up front would make the safeguard
    an obstacle rather than a check.  The refusal happens at the point of use, where a
    policy has actually escalated a case and the rates are about to become a number.
    """
    if args.alternate_qualification:
        evidence = load_artifact(args.alternate_qualification)
        return AlternateCharacteristics(
            sensitivity=evidence.sensitivity,
            false_positive_rate=evidence.false_positive_rate,
            qualification_ref=Path(args.alternate_qualification).name,
        )
    if args.assume_alternate_rates:
        sensitivity, fpr = args.assume_alternate_rates
        return AlternateCharacteristics(
            sensitivity=sensitivity,
            false_positive_rate=fpr,
            assumed_because="--assume-alternate-rates on the command line",
        )
    return AlternateCharacteristics()


def _benchmark_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="assurance-plan benchmark-policies")
    parser.add_argument("runs", help="path to a per-case evaluator outcomes YAML file")
    parser.add_argument("--max-error", type=float, default=0.05)
    parser.add_argument("--max-replications", type=int, default=12)
    parser.add_argument(
        "--folds",
        type=int,
        default=5,
        help=(
            "cross-validation folds. Every case is scored by a policy calibrated "
            "without it. Default: 5"
        ),
    )
    parser.add_argument(
        "--budget",
        type=int,
        default=8,
        help=(
            "the repetition budget the fixed-N and early-stopping policies are given. "
            "Default: 8, because that is the historical operating practice under test"
        ),
    )
    #: Every one of these is an assumption.  They are flags rather than constants
    #: because the whole question of which policy wins is downstream of them, and a
    #: reader should be able to find out how little it takes to flip the answer.
    parser.add_argument("--judge-cost", type=float, default=_DEFAULT_COST.judge_cost_usd)
    parser.add_argument(
        "--judge-latency", type=float, default=_DEFAULT_COST.judge_latency_seconds
    )
    parser.add_argument(
        "--judge-parallelism", type=int, default=_DEFAULT_COST.judge_parallelism
    )
    parser.add_argument(
        "--alternate-cost", type=float, default=_DEFAULT_COST.alternate_cost_usd
    )
    #: The alternate's accuracy is either measured or explicitly assumed, and there is
    #: no third option.  ``--alternate-sensitivity`` used to default to 0.95 with no
    #: mention of where 0.95 came from; a policy that escalates now fails unless one of
    #: these two flags is given, because that default was the leak.
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--alternate-qualification",
        metavar="PATH",
        help=(
            "an alternate qualification artifact from 'characterize-alternate --emit'. "
            "Its counts supply the alternate's sensitivity and false-positive rate"
        ),
    )
    source.add_argument(
        "--assume-alternate-rates",
        nargs=2,
        type=float,
        metavar=("SENSITIVITY", "FPR"),
        help=(
            "model the alternate's accuracy instead of measuring it. Every number "
            "derived from it is labelled ASSUMED in the report"
        ),
    )
    parser.add_argument("--human-cost", type=float, default=_DEFAULT_COST.human_cost_usd)
    args = parser.parse_args(argv)

    cost = CostModel(
        judge_cost_usd=args.judge_cost,
        judge_latency_seconds=args.judge_latency,
        judge_parallelism=args.judge_parallelism,
        alternate_cost_usd=args.alternate_cost,
        alternate=_alternate_characteristics(args),
        human_cost_usd=args.human_cost,
    )

    run = load_characterization(args.runs)
    analysis = characterize(run, args.max_error, args.max_replications)
    policies = default_policies(args.budget)
    try:
        results, leakage = compare(run, policies, cost, k=args.folds)
    except UnqualifiedAlternateError as error:
        #: Reported, not raised as a traceback: this is a missing-input condition, and
        #: a stack trace invites the reader to look for a bug in the code instead of
        #: for the experiment nobody ran.
        print(f"refusing to report modelled escalation error:\n\n{error}", file=sys.stderr)
        return 3
    folds = stratified_folds(run, k=args.folds)
    #: ``compare`` appends the blind escalation control itself; rebuild it here so the
    #: allocation diagnostic covers it too, since "is the targeting doing anything" is
    #: exactly a question about which cases the calls went to.
    control = matched_control(results, len(run.cases), args.budget)
    if control is not None:
        policies += (control,)

    print("=" * 78)
    print(f"Policy benchmark :: {run.evaluator_version}")
    print("=" * 78)
    print(
        render_benchmark(
            run=run,
            analysis=analysis,
            results=results,
            leakage=leakage,
            marginal=marginal_value(run, cost, args.budget),
            slices=slice_diagnostics(run),
            allocation=tuple(
                allocation_diagnostic(run, policy, cost, folds) for policy in policies
            ),
            fits=fit_by_reference_label(run),
            warnings=sample_size_warnings(run),
            cost=cost,
        )
    )
    #: Non-zero when the comparison cannot be trusted, so a pipeline cannot quietly
    #: consume a leaking or under-powered result.
    if not leakage.clean:
        return 2
    return 1 if sample_size_warnings(run) else 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "characterize-evaluator":
        return _characterize_command(argv[1:])
    if argv and argv[0] == "characterize-alternate":
        return _alternate_command(argv[1:])
    if argv and argv[0] == "benchmark-policies":
        return _benchmark_command(argv[1:])
    return _plan_command(argv)


if __name__ == "__main__":
    sys.exit(main())
