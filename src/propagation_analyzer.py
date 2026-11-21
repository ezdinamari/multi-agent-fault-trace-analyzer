
from collections import defaultdict, deque
from datetime import datetime
from typing import Any

from .failure_detector import (
    is_contaminated_final_output,
    is_observable_failure,
)


def _timestamp_key(event: dict[str, Any]) -> tuple[int, str]:
    """Sort valid ISO timestamps chronologically; malformed values sort last."""
    value = str(event.get("timestamp", ""))
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return (0, parsed.isoformat())
    except ValueError:
        return (1, value)


def _parents(event: dict[str, Any]) -> list[str]:
    result: list[str] = []

    parent = event.get("parent_event_id")
    if parent:
        result.append(str(parent))

    depends_on = event.get("depends_on", [])
    if isinstance(depends_on, list):
        result.extend(str(item) for item in depends_on if item)

    return list(dict.fromkeys(result))


def analyze_run(events: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Analyze one run using explicit causal references.

    Semantic propagation requires explicit annotations or an independently
    labelled contaminated final output. Causal reachability alone is not
    considered proof of semantic propagation.
    """
    if not events:
        raise ValueError("Cannot analyze an empty run")

    run_ids = {str(event["run_id"]) for event in events}
    if len(run_ids) != 1:
        raise ValueError("analyze_run expects events from exactly one run")

    by_id = {str(event["event_id"]): event for event in events}
    children: dict[str, list[str]] = defaultdict(list)
    dangling_references: list[dict[str, str]] = []

    for event in events:
        child_id = str(event["event_id"])

        for parent_id in _parents(event):
            if parent_id not in by_id:
                dangling_references.append({
                    "event_id": child_id,
                    "missing_parent_event_id": parent_id,
                })
            else:
                children[parent_id].append(child_id)

    candidates = [
        event for event in events
        if is_observable_failure(event)
    ]
    candidates.sort(key=_timestamp_key)

    # Prefer an explicitly marked injected fault as the root.
    injected = [
        event for event in candidates
        if event.get("injected_fault") is True
    ]
    root = injected[0] if injected else (
        candidates[0] if candidates else None
    )

    if root is None:
        return {
            "run_id": str(events[0]["run_id"]),
            "has_observable_failure": False,
            "root_cause_event_id": None,
            "root_cause_agent": None,
            "downstream_event_ids": [],
            "downstream_agents": [],
            "affected_events_count": 0,
            "affected_agents_count": 0,
            "propagation_depth": 0,
            "fault_propagated": False,
            "final_output_contaminated": False,
            "dangling_references": dangling_references,
            "note": "No observable failure signal was found in the supplied trace.",
        }

    root_id = str(root["event_id"])
    root_agent = root.get("agent")

    # Compute causal reachability and shortest dependency distance from root.
    distances: dict[str, int] = {}
    queue = deque(
        (child_id, 1)
        for child_id in children.get(root_id, [])
    )

    while queue:
        event_id, depth = queue.popleft()

        if event_id in distances:
            continue

        distances[event_id] = depth

        for child_id in children.get(event_id, []):
            if child_id not in distances:
                queue.append((child_id, depth + 1))

    downstream_events = [
        by_id[event_id] for event_id in distances
    ]
    downstream_events.sort(key=_timestamp_key)

    # Explicit annotations are required for semantic propagation.
    propagation_events = [
        event for event in downstream_events
        if event.get("consumed_faulty_information") is True
        or event.get("propagated_fault") is True
    ]

    downstream_agents = sorted({
        str(event["agent"])
        for event in propagation_events
        if event.get("agent") is not None
        and event.get("agent") != root_agent
    })

    affected_event_ids = sorted({
        str(event["event_id"])
        for event in propagation_events
    })

    # Maximum shortest-path distance to an explicitly affected event.
    propagation_depth = max(
        (
            distances[event_id]
            for event_id in affected_event_ids
        ),
        default=0,
    )

    contaminated_final = any(
        is_contaminated_final_output(event)
        for event in downstream_events
    )

    fault_propagated = (
        bool(propagation_events) or contaminated_final
    )

    return {
        "run_id": str(events[0]["run_id"]),
        "has_observable_failure": True,
        "root_cause_event_id": root_id,
        "root_cause_agent": root_agent,
        "root_cause_event_type": root.get("event_type"),
        "injected_fault": root.get("injected_fault") is True,
        "fault_type": root.get("fault_type"),
        "downstream_event_ids": sorted(distances),
        "downstream_agents": downstream_agents,
        "affected_event_ids": affected_event_ids,
        "affected_events_count": len(affected_event_ids),
        "affected_agents_count": len(downstream_agents),
        "propagation_depth": propagation_depth,
        "fault_propagated": fault_propagated,
        "final_output_contaminated": contaminated_final,
        "dangling_references": dangling_references,
        "note": (
            "Causal reachability is inferred from explicit dependencies. "
            "Semantic propagation requires consumed_faulty_information or "
            "propagated_fault annotations, or an independently labelled "
            "contaminated final output. Propagation depth is the maximum "
            "shortest-path distance to an explicitly affected event."
        ),
    }


def summarize_runs(
    run_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute run-level fault propagation statistics."""

    injected_runs = [
        result for result in run_results
        if result.get("injected_fault") is True
    ]

    propagated = [
        result for result in injected_runs
        if result.get("fault_propagated") is True
    ]

    denominator = len(injected_runs)

    affected_agents_total = sum(
        result.get("affected_agents_count", 0)
        for result in injected_runs
    )

    affected_events_total = sum(
        result.get("affected_events_count", 0)
        for result in injected_runs
    )

    depths = [
        result.get("propagation_depth", 0)
        for result in injected_runs
    ]

    return {
        "number_of_runs": len(run_results),
        "runs_with_observable_failure": sum(
            bool(result.get("has_observable_failure"))
            for result in run_results
        ),
        "fault_injected_runs": denominator,
        "fault_propagated_runs": len(propagated),
        "fault_propagation_rate": (
            len(propagated) / denominator if denominator else None
        ),
        "final_outputs_contaminated": sum(
            bool(result.get("final_output_contaminated"))
            for result in injected_runs
        ),
        "affected_agents_total": affected_agents_total,
        "affected_events_total": affected_events_total,
        "average_affected_agents_per_injected_run": (
            affected_agents_total / denominator if denominator else None
        ),
        "average_affected_events_per_injected_run": (
            affected_events_total / denominator if denominator else None
        ),
        "maximum_propagation_depth": max(depths, default=0),
        "average_propagation_depth": (
            sum(depths) / denominator if denominator else None
        ),
    }
