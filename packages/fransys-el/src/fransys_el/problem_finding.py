"""The `PLACEMENT_PROBLEM` or `SYMBOL_PORT_MISSING` finding of a `ProblemError`, its subjects model Ids (Ruling 28 Q1)."""

from typing import TYPE_CHECKING

from fransys_model.derive import item_functions, subject_part_mpn, symbol_port_subject
lazy from fransys_model.kernel import Finding

from .codes import FINDING_CODES
from .placement_ids import symbol_key
from .placement_kit import PortMissingError

if TYPE_CHECKING:
    from fransys_model.kernel import Model

    from .placement_kit import ProblemError

__all__ = ["problem_finding"]

_INFO = {i.code: i for i in FINDING_CODES}


def problem_finding(error: ProblemError, model: Model) -> Finding:
    """One `PLACEMENT_PROBLEM` `ERROR`; its subject is the function whose symbol key `error` names.

    The key-to-Id map is this one: a symbol id is its function's `render_id` (S1). A key that
    names no function of `model`, or no key, leaves the subjects empty. A `PortMissingError` is
    one `SYMBOL_PORT_MISSING` `ERROR` against its port template (decision 0018, model-0283).
    """
    if isinstance(error, PortMissingError):
        mpn = subject_part_mpn(model, error.function) or "no part"
        subject = symbol_port_subject(model, error.function, error.port_name)
        message = f"part {mpn!r}: model port {error.port_name!r} has no port on symbol {error.symbol!r}"
        return _INFO["SYMBOL_PORT_MISSING"].finding((subject,), message)
    by_key = {symbol_key(model, function): function for members in item_functions(model).values() for function in members}
    subject = by_key.get(error.key) if error.key is not None else None
    return _INFO["PLACEMENT_PROBLEM"].finding(() if subject is None else (subject,), str(error))
