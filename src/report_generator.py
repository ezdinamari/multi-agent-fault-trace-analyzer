import json
from pathlib import Path
from typing import Any


def write_report(report: dict[str, Any], output_path: str | Path) -> Path:
    """Write the complete analysis report as formatted JSON."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output
