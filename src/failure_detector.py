from typing import Any


FAILURE_STATUSES = {"error", "failed", "timeout", "timed_out"}
INVALID_VALIDATION_STATES = {"invalid", "incorrect", "inconsistent"}


def is_observable_failure(event: dict[str, Any]) -> bool:
    """
    Identify an observable failure signal.

    This is intentionally conservative: a fault injection marker is evidence
    that a fault was introduced, while status/validation fields indicate an
    observable failure. A fault marker alone does not prove propagation.
    """
    if event.get("injected_fault") is True:
        return True

    status = str(event.get("status", "")).lower()
    if status in FAILURE_STATUSES:
        return True

    validation = str(event.get("validation_status", "")).lower()
    if validation in INVALID_VALIDATION_STATES:
        return True

    return event.get("is_failure") is True


def is_contaminated_final_output(event: dict[str, Any]) -> bool:
    if event.get("event_type") != "final_output":
        return False

    if event.get("contains_faulty_information") is True:
        return True

    if event.get("correctness") is False:
        return True

    validation = str(event.get("validation_status", "")).lower()
    return validation in INVALID_VALIDATION_STATES
