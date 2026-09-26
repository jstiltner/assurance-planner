"""assurance-plan <scenario.yaml> [--context NAME]

    assurance-plan characterize-evaluator <runs.yaml> [--max-error E]
"""

from __future__ import annotations

import argparse
import sys

from .characterization import characterize
from .loader import load, load_characterization
from .planner import plan
from .rationale import render, render_characterization

SUBCOMMANDS = ("characterize-evaluator",)


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


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "characterize-evaluator":
        return _characterize_command(argv[1:])
    return _plan_command(argv)


if __name__ == "__main__":
    sys.exit(main())
