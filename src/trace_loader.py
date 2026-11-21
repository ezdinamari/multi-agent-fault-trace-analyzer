import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {"run_id", "event_id", "timestamp", "event_type"}


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    """Load JSONL events and perform basic schema validation."""
    path = Path(path)
    events: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{path}:{line_number}: invalid JSON: {exc.msg}"
                ) from exc

            if not isinstance(event, dict):
                raise ValueError(f"{path}:{line_number}: each JSONL row must be an object")

            missing = REQUIRED_FIELDS - event.keys()
            if missing:
                raise ValueError(
                    f"{path}:{line_number}: missing required fields: {sorted(missing)}"
                )

            events.append(event)

    if not events:
        raise ValueError(f"{path}: no events found")

    return events
