from collections import defaultdict
from typing import Any


def normalize_events(events: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group events by run and reject duplicate event IDs within a run."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for event in events:
        run_id = str(event["run_id"])
        grouped[run_id].append(event)

    for run_id, run_events in grouped.items():
        seen: set[str] = set()
        for event in run_events:
            event_id = str(event["event_id"])
            if event_id in seen:
                raise ValueError(
                    f"Run {run_id!r} contains duplicate event_id {event_id!r}"
                )
            seen.add(event_id)

    return dict(grouped)
