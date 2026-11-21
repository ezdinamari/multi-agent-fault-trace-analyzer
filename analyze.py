
import argparse
import json
from pathlib import Path

from src.event_normalizer import normalize_events
from src.propagation_analyzer import analyze_run, summarize_runs
from src.report_generator import write_report
from src.trace_loader import load_jsonl
from src.graph_visualizer import write_graph


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze causal fault propagation in multi-agent JSONL traces."
    )
    parser.add_argument("input", help="Path to a JSONL trace file")
    parser.add_argument(
        "--output",
        default="results/analysis.json",
        help="Output JSON path (default: results/analysis.json)",
    )
    args = parser.parse_args()

    events = load_jsonl(args.input)
    grouped = normalize_events(events)

    run_results = []

    graph_dir = Path(args.output).parent / "graphs"

    for run_id, run_events in sorted(grouped.items()):
        analysis = analyze_run(run_events)
        run_results.append(analysis)

        safe_run_id = "".join(
            char if char.isalnum() else "_"
            for char in str(run_id)
        )

        graph_path = graph_dir / f"run_{safe_run_id}.mmd"

        write_graph(
            run_events,
            analysis,
            str(graph_path),
        )

        print(f"Graph generated: {graph_path}")

    report = {
        "input_file": args.input,
        "summary": summarize_runs(run_results),
        "runs": run_results,
    }

    output_path = write_report(report, args.output)

    print(json.dumps(report["summary"], indent=2))
    print(f"\nDetailed report written to: {output_path}")


if __name__ == "__main__":
    main()
