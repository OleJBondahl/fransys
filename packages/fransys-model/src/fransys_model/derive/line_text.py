"""Texts of a harness line: its designation and a leaving line's one stub."""

from fransys_model.kernel import Id, Model, SchemaError
lazy from fransys_model.vocab.core import Item, Unit

from .designation import printed_designation
from .drawing_text import line_stub_line
from .harness_line_ends import harness_line_ends

_PLAIN_LINE = 2  # a line between two ends carries no branch number


def line_designation(
    model: Model, harness: Id[Item], branch: int, *, unit: Id[Unit] | None = None
) -> str:
    """`-W13` for a line between two ends, `-W13.n` on each branch of three or more, else `""`.

    `branch` is the `HarnessLineEnd.branch` of the end; this never numbers on its own.
    Raises `SchemaError` when `branch` is no branch of the line.
    """
    count = len(harness_line_ends(model, harness))
    if not 1 <= branch <= max(count, 1):
        msg = f"{harness}: branch {branch} is not one of its {count} ends"
        raise SchemaError(msg, kind="item", record_id=harness)
    if count < _PLAIN_LINE:
        return ""
    designation = printed_designation(model, harness, unit=unit)
    return designation if count == _PLAIN_LINE else f"{designation}.{branch}"


__all__ = ["line_designation", "line_stub_line"]
