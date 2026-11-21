
from pathlib import Path
from typing import Any


def _safe_id(value: str) -> str:
    """Convert an event ID into a Mermaid-safe node identifier."""
    return "".join(
        char if char.isalnum() else "_"
        for char in str(value)
    )


def _escape_label(value: Any) -> str:
    """Escape text for use inside Mermaid node labels."""
    return (
        str(value)
        .replace("&", "&amp;")
        .replace('"', "#quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", " ")
        .replace("|", "/")
    )


def _parents(event: dict[str, Any]) -> list[str]:
    parents = []

    parent = event.get("parent_event_id")
    if parent:
        parents.append(str(parent))

    dependencies = event.get("depends_on", [])
    if isinstance(dependencies, list):
        parents.extend(str(item) for item in dependencies if item)

    return list(dict.fromkeys(parents))


def generate_mermaid(
    events: list[dict[str, Any]],
    analysis: dict[str, Any],
) -> str:
    """Generate a Mermaid causal dependency graph for one analyzed run."""

    if not events:
        raise ValueError("Cannot visualize an empty run")

    root_id = analysis.get("root_cause_event_id")
    contaminated = analysis.get("final_output_contaminated", False)

    lines = [
        "flowchart TD",
        "    %% Causal dependency graph",
    ]

    propagation_ids = {
        str(event["event_id"])
        for event in events
        if event.get("consumed_faulty_information") is True
        or event.get("propagated_fault") is True
    }

    for event in events:
        event_id = str(event["event_id"])
        node_id = "event_" + _safe_id(event_id)

        agent = _escape_label(event.get("agent", "Unknown agent"))
        event_type = _escape_label(event.get("event_type", "event"))

        label = f"{agent}: {event_type}\\nID: {_escape_label(event_id)}"

        lines.append(f'    {node_id}["{label}"]')

        if event_id == str(root_id):
            lines.append(f"    style {node_id} fill:#f8b4b4,stroke:#b91c1c,stroke-width:3px")
        elif event_id in propagation_ids:
            lines.append(f"    style {node_id} fill:#fed7aa,stroke:#c2410c,stroke-width:2px")

        if event.get("is_final_output") is True:
            if contaminated:
                lines.append(f"    style {node_id} fill:#e9d5ff,stroke:#7e22ce,stroke-width:3px")
            else:
                lines.append(f"    style {node_id} fill:#bbf7d0,stroke:#15803d,stroke-width:2px")

    known_ids = {str(event["event_id"]) for event in events}

    for event in events:
        child_id = str(event["event_id"])
        child_node = "event_" + _safe_id(child_id)

        for parent_id in _parents(event):
            if parent_id in known_ids:
                parent_node = "event_" + _safe_id(parent_id)
                lines.append(f"    {parent_node} --> {child_node}")

    lines.extend([
        "",
        "    %% Legend",
        "    classDef root fill:#f8b4b4,stroke:#b91c1c,stroke-width:3px",
        "    classDef propagated fill:#fed7aa,stroke:#c2410c,stroke-width:2px",
        "    classDef normal fill:#e5e7eb,stroke:#6b7280",
    ])

    return "\n".join(lines) + "\n"


def write_graph(
    events: list[dict[str, Any]],
    analysis: dict[str, Any],
    output_path: str,
) -> str:
    """Write the Mermaid graph to disk."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    graph = generate_mermaid(events, analysis)
    path.write_text(graph, encoding="utf-8")

    return str(path)
