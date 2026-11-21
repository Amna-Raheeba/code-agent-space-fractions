"""Command-line entry point: python -m agent.

Reads the two architecture documents, preprocesses them to JSON, and
runs the agent loop. The API key comes from an environment variable
or the --api-key flag. It is never written to a file.

The model is DeepSeek deepseek-v4-pro through the official DeepSeek
API, exactly as the task requires. There is no other provider.
"""

import argparse
import os
import sys

from . import config
from .budget import Budget
from .loop import run_agent
from .preprocess import preprocess


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Code Agent: generate a project from architecture documents."
    )
    parser.add_argument("--doc", required=True, help="Architecture document (.md).")
    parser.add_argument("--view", required=True, help="Architecture views (.md).")
    parser.add_argument("--output", required=True, help="Output folder for the project.")
    parser.add_argument("--work-dir", default=".", help="Working folder (default: current).")
    parser.add_argument("--api-key", default=None, help="DeepSeek API key (or set DEEPSEEK_API_KEY).")
    parser.add_argument("--task", default=None, help="Extra instructions for the agent.")
    parser.add_argument(
        "--max-turns",
        type=int,
        default=config.MAX_TURNS,
        help="Maximum agent turns (default {}).".format(config.MAX_TURNS),
    )
    args = parser.parse_args(argv)

    api_key = args.api_key or os.environ.get(config.API_KEY_ENV_VAR)
    if not api_key:
        print(
            "No DeepSeek API key. Pass --api-key or set {}.".format(
                config.API_KEY_ENV_VAR
            ),
            file=sys.stderr,
        )
        return 2

    try:
        spec = preprocess(args.doc, args.view)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    budget = Budget()
    events = []

    def on_event(kind, text):
        events.append((kind, text))
        if kind in ("call", "tool", "cost", "info"):
            print("[{}] {}".format(kind, text))

    result = run_agent(
        spec,
        work_dir=args.work_dir,
        output_dir=args.output,
        api_key=api_key,
        budget=budget,
        on_event=on_event,
        max_turns=args.max_turns,
        extra_instructions=args.task,
    )

    print()
    print("Status: {}".format(result.status))
    print("Turns: {}".format(result.turns))
    print("Cost: {}".format(result.budget.summary()))
    print("Files written: {}".format(len(result.files_written)))
    for name in result.files_written:
        print("  - {}".format(name))
    print()
    print(result.final_text)
    return 0 if result.status == "done" else 1


if __name__ == "__main__":
    raise SystemExit(main())
