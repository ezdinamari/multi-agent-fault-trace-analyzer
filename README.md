# Multi-Agent Fault Trace Analyzer

A small research prototype for analyzing **causal fault propagation** in multi-agent execution traces.

It complements an MCP fault-injection demonstrator by focusing on the next question:

> Once a fault occurs, which downstream agents depend on it, and does it contaminate the final output?

## Scope

The prototype:

1. Loads JSONL execution traces.
2. Groups events by run and checks event-ID uniqueness.
3. Uses explicit causal references (`parent_event_id` and `depends_on`) to construct an event-dependency graph.
4. Identifies the earliest explicitly injected fault (or earliest observable failure when no injection marker exists).
5. Finds downstream events and agents reachable from that event.
6. Checks whether a downstream final output is marked incorrect or contaminated.
7. Calculates a run-level fault propagation rate.

It uses synthetic example traces and the Python standard library. It does **not** connect to CrewAI, LangGraph, or a live MCP server.

## Quick start

Python 3.10+ is recommended. No third-party dependencies are required.

```bash
python analyze.py examples/semantic_corruption.jsonl
```

Expected summary:

```json
{
  "number_of_runs": 1,
  "runs_with_observable_failure": 1,
  "fault_injected_runs": 1,
  "fault_propagated_runs": 1,
  "fault_propagation_rate": 1.0,
  "final_outputs_contaminated": 1
}
```

Analyze the contained-fault example:

```bash
python analyze.py examples/no_propagation.jsonl --output results/no_propagation_report.json
```

Run tests:

```bash
python -m unittest discover -s tests -v
```

## Trace schema

Each line is one JSON object. Required fields:

| Field | Meaning |
|---|---|
| `run_id` | Identifier for one workflow execution |
| `event_id` | Unique event identifier within the run |
| `timestamp` | ISO-8601 timestamp |
| `event_type` | For example `tool_call`, `tool_result`, `agent_message`, `final_output` |

Optional fields:

| Field | Meaning |
|---|---|
| `agent` | Agent responsible for the event |
| `parent_event_id` | Direct causal parent event |
| `depends_on` | List of additional causal parent event IDs |
| `injected_fault` | `true` when the injector intentionally introduced a fault at this event |
| `fault_type` | Fault category, e.g. `semantic_corruption` |
| `status` | E.g. `success`, `error`, `timeout` |
| `validation_status` | E.g. `valid`, `invalid`, `inconsistent` |
| `correctness` | Boolean correctness label for a final output |
| `contains_faulty_information` | Boolean indicating final-output contamination |
| `consumed_faulty_information` | Explicit annotation that an agent used faulty information |
| `propagated_fault` | Explicit annotation that an event carries the injected fault onward |

**Important:** timestamps alone are not treated as proof of causal dependency. For propagation analysis, traces must preserve parent/depends-on references. If these links are missing, propagation may be undercounted.

## Metric

For a set of runs containing injected faults:

\[
FPR =
\frac{\text{fault-injected runs with downstream propagation}}
{\text{all runs containing an injected fault}}
\]

A run is marked as propagated when a causally reachable downstream event is explicitly annotated with `consumed_faulty_information: true` or `propagated_fault: true`, or when a causally reachable final output is independently labelled as contaminated.

Causal reachability alone is not treated as proof that an agent used faulty information. The annotations should be produced by instrumentation, independent validation, or careful trace review. This is a prototype operational definition, not an automatic semantic-influence detector.

## Interpretation and limitations

- A fault-injection marker identifies where the experiment introduced a fault; it does not by itself prove that the fault affected later agents.
- The analyzer reports the earliest observable failure signal, preferring an explicitly marked injection event when available.
- The analyzer does not infer causality from timestamps or text similarity.
- Incorrectness labels must come from independent validation, ground truth, or carefully reviewed annotations.
- The current prototype uses a single-root analysis per run. Runs with multiple independent injected faults should be analyzed separately or extended to support multiple roots.
- The tool does not yet perform statistical confidence intervals, automatic trace instrumentation, or framework-specific parsing.

## Research extension

A natural next step is to add adapters that convert CrewAI and LangGraph traces into this normalized schema, then validate propagation labels against manually reviewed traces and independently verified task outputs.
