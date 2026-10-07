"""Texts of a harness line: its designation and a leaving line's one stub (HL1, HL3)."""

from fransys_model.kernel import Id, Model, SchemaError
lazy from fransys_model.vocab.core import Item, Unit

from .designation import printed_designation
from .drawing_text import off_stub_line
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


def line_stub_line(line: str, *, north: bool, far: str) -> str:
    """A leaving line's single stub, `-W3 → +EXT-M1`: the line, an arrow, the far device.

    Beside `off_stub_line`, which prints one stub per core with the far ports. The arrow
    points up (`←`) for a stub facing north, else `→`.
    """
    return off_stub_line(line, north=north, far=far, ports=())


__all__ = ["line_designation", "line_stub_line"]
