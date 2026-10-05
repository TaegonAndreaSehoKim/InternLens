from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.ranking.evaluation import evaluate_benchmark


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate labeled ranking regression cases at a fixed time.")
    parser.add_argument("--benchmark", type=Path, default=PROJECT_ROOT / "tests/fixtures/ranking_benchmark.json")
    parser.add_argument("--output-file", type=Path)
    parser.add_argument("--check", action="store_true", help="Exit nonzero when any profile misses a threshold.")
    args = parser.parse_args()
    report = evaluate_benchmark(json.loads(args.benchmark.read_text(encoding="utf-8")))
    if args.output_file:
        args.output_file.parent.mkdir(parents=True, exist_ok=True)
        args.output_file.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"{report['benchmark']}: {report['judgment_count']} judgments across {len(report['profiles'])} profiles")
    for metric, value in report["macro_metrics"].items():
        print(f"{metric}: {value:.4f}")
    for failure in report["failures"]:
        print(f"FAILED {failure['profile_name']}/{failure['metric']}: {failure['actual']:.4f}, threshold {failure['threshold']:.4f}")
    print("PASS" if report["passed"] else "FAIL")
    if args.check and not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
