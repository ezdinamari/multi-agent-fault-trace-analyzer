
import argparse
import json
from pathlib import Path
from typing import Any


def load_report(path: str) -> dict[str, Any]:
    """Load an existing JSON report."""
    with open(path, "r", encoding="utf-8") as file:
        report = json.load(file)

    if not isinstance(report.get("runs"), list):
        raise ValueError(f"Invalid report: missing runs list in {path}")

    return report


def wilson_interval(
    successes: int,
    total: int,
    z: float = 1.96,
) -> list[float] | None:
    """Calculate a 95% Wilson confidence interval for a proportion."""
    if total == 0:
        return None

    p = successes / total
    denominator = 1 + z**2 / total

    center = (
        p + z**2 / (2 * total)
    ) / denominator

    margin = (
        z
        * (
            p * (1 - p) / total
            + z**2 / (4 * total**2)
        ) ** 0.5
        / denominator
    )

    return [
        max(0.0, center - margin),
        min(1.0, center + margin),
    ]


def analyze_condition(
    name: str,
    report_path: str,
) -> dict[str, Any]:
    """Calculate metrics from individual injected-fault runs."""

    report = load_report(report_path)

    all_runs = report["runs"]

    injected_runs = [
        run for run in all_runs
        if run.get("injected_fault") is True
    ]

    total = len(injected_runs)

    propagated_runs = [
        run for run in injected_runs
        if run.get("fault_propagated") is True
    ]

    contaminated_runs = [
        run for run in injected_runs
        if run.get("final_output_contaminated") is True
    ]

    propagation_rate = (
        len(propagated_runs) / total if total else None
    )

    contamination_rate = (
        len(contaminated_runs) / total if total else None
    )

    def average(field: str) -> float | None:
        if not total:
            return None

        return sum(
            run.get(field, 0) or 0
            for run in injected_runs
        ) / total

    return {
        "condition": name,
        "source_report": report_path,
        "total_runs": len(all_runs),
        "injected_fault_runs": total,
        "propagated_runs": len(propagated_runs),
        "propagation_rate": propagation_rate,
        "propagation_rate_95_ci": wilson_interval(
            len(propagated_runs),
            total,
        ),
        "contaminated_runs": len(contaminated_runs),
        "contamination_rate": contamination_rate,
        "average_affected_agents": average(
            "affected_agents_count"
        ),
        "average_affected_events": average(
            "affected_events_count"
        ),
        "average_propagation_depth": average(
            "propagation_depth"
        ),
    }


def compare_conditions(
    reference: dict[str, Any],
    conditions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare each condition against a reference condition."""

    comparisons = []

    reference_rate = reference["propagation_rate"]

    for condition in conditions:
        condition_rate = condition["propagation_rate"]

        if (
            reference_rate is not None
            and condition_rate is not None
        ):
            difference = condition_rate - reference_rate

            relative_reduction = (
                (reference_rate - condition_rate) / reference_rate
                if reference_rate > 0
                else None
            )
        else:
            difference = None
            relative_reduction = None

        comparisons.append({
            "condition": condition["condition"],
            "reference_condition": reference["condition"],
            "propagation_rate_difference": difference,
            "relative_propagation_reduction": relative_reduction,
        })

    return {
        "reference": reference,
        "conditions": conditions,
        "comparisons": comparisons,
        "methodological_note": (
            "Rates are calculated using injected-fault runs only. "
            "Confidence intervals use the Wilson score method. "
            "Comparisons are descriptive and do not establish causality "
            "without controlled, matched experimental conditions."
        ),
    }


def parse_condition(value: str) -> tuple[str, str]:
    """Parse NAME=PATH arguments."""
    if "=" not in value:
        raise argparse.ArgumentTypeError(
            "Expected NAME=PATH"
        )

    name, path = value.split("=", 1)

    if not name.strip() or not path.strip():
        raise argparse.ArgumentTypeError(
            "Both condition name and path are required"
        )

    return name.strip(), path.strip()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare multi-agent fault-injection experiments."
    )

    parser.add_argument(
        "--reference",
        required=True,
        type=parse_condition,
        help="Reference condition in NAME=PATH format",
    )

    parser.add_argument(
        "--condition",
        action="append",
        required=True,
        type=parse_condition,
        help="Comparison condition in NAME=PATH format. Repeatable.",
    )

    parser.add_argument(
        "--output",
        default="results/experiment_comparison.json",
        help="Output JSON path",
    )

    args = parser.parse_args()

    reference_name, reference_path = args.reference

    reference = analyze_condition(
        reference_name,
        reference_path,
    )

    conditions = [
        analyze_condition(name, path)
        for name, path in args.condition
    ]

    result = compare_conditions(reference, conditions)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(result, file, indent=2)

    print(json.dumps(result, indent=2))
    print(f"\nComparison report written to: {output_path}")


if __name__ == "__main__":
    main()
