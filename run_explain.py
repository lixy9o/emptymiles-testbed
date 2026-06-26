#!/usr/bin/env python3
"""Module-C demo: run the scored matcher and print *why* it made each match.

    python run_explain.py
"""

from src.emptymiles_testbed.config import Config
from src.emptymiles_testbed.generator import generate
from src.emptymiles_testbed.strategies.scored import ScoredGreedy


def main() -> None:
    cfg = Config()
    scenario = generate(cfg)
    matcher = ScoredGreedy()
    assignments = matcher.match(scenario, cfg)

    matched = sorted(oid for oid, rid in assignments.items() if rid is not None)
    dedicated = [oid for oid, rid in assignments.items() if rid is None]

    print(f"Scored matcher: {len(matched)} matched, {len(dedicated)} left dedicated.\n")
    print("Why these matches (first 8):\n")
    for oid in matched[:8]:
        e = matcher.explanations[oid]
        print(f"  order {oid:>3} → route {e.route_id:<3}  (score {e.score:+.2f})")
        for reason in e.reasons:
            print(f"        • {reason}")
        print()


if __name__ == "__main__":
    main()
