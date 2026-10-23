"""The `PLACEMENT_PROBLEM` finding of a `ProblemError`, its subjects model Ids (Ruling 28 Q1)."""

from typing import TYPE_CHECKING

from fransys_model.derive import item_functions
from fransys_model.kernel import Finding, Severity

from .codes import FINDING_CODES
from .placement_ids import symbol_key

if TYPE_CHECKING:
    from fransys_model.kernel import Model

    from .placement_kit import ProblemError

__all__ = ["problem_finding"]

_FIX = next(i for i in FINDING_CODES if i.code == "PLACEMENT_PROBLEM").filled()


def problem_finding(error: ProblemError, model: Model) -> Finding:
    """One `PLACEMENT_PROBLEM` `ERROR`; its subject is the function whose symbol key `error` names.

    The key-to-Id map is this one: a symbol id is its function's `render_id` (S1). A key that
    names no function of `model`, or no key, leaves the subjects empty.
    """
    by_key = {
        symbol_key(model, function): function
        for members in item_functions(model).values()
        for function in members
    }
    subject = by_key.get(error.key) if error.key is not None else None
    return Finding(
        code="PLACEMENT_PROBLEM",
        severity=Severity.ERROR,
        subjects=() if subject is None else (subject,),
        fix=_FIX,
        message=str(error),
    )
