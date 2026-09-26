"""assurance-plan <scenario.yaml> [--context NAME]"""

from __future__ import annotations

import argparse
import sys

from .loader import load
from .planner import plan
from .rationale import render


def main(argv: list[str] | None = None) -> int:
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


if __name__ == "__main__":
    sys.exit(main())
