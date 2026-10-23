"""The texts the overview prints on a line and on a leaving stub (model-0198).

One function each, so the engine that measures a text and the page that prints it agree.
Re-exported from `fransys_model.derive`, not from the consumer `fr.derive` facade (model-0197).
"""

lazy from collections.abc import Sequence

lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.layout import StubText
lazy from fransys_model.vocab.core import Item, Unit

from .designation import printed_designation
from .drawing_text import off_stub_line
from .overview_names import display_unit
from .rows import OverviewLine, OverviewLinkKind, OverviewStub
lazy from .rows_overview import FieldJoin, FoldLine, FoldStub, LocationLine, StubPlace


def _count_text(kind: OverviewLinkKind, count: int) -> str:
    """`x 3` for a wire or mate line that stands for several connections, else empty."""
    return f"x {count}" if count > 1 and kind is not OverviewLinkKind.CABLE else ""


def overview_lifted_text(kind: OverviewLinkKind, carriers: Sequence[str], count: int) -> str:
    """The one text of a line for `count` connections carried by cables printed `carriers`.

    One carrier prints its designation, several print `x N` for N carriers, none print the count
    text (`x 3` for a wire or mate line of three, else empty). Every level's lifted lines use it.
    """
    if not carriers:
        return _count_text(kind, count)
    return carriers[0] if len(carriers) == 1 else f"x {len(carriers)}"


def overview_field_join_text(model: Model, join: FieldJoin) -> str:
    """The text of a field box's lifted line: its cables as `overview_lifted_text` prints them."""
    carriers = tuple(printed_designation(model, cable) for cable in join.cables)
    return overview_lifted_text(join.kind, carriers, join.count)


def overview_line_text(line: OverviewLine) -> str:
    """The text of a line: its carrier's designation, else the count text."""
    return overview_lifted_text(line.ref.kind, (line.label,) if line.label else (), line.count)


def overview_end_text(
    model: Model, unit: Id[Unit], kind: OverviewLinkKind, via: Id[Item] | None, count: int
) -> str:
    """The text of a line to a stub: its carrier relative to `unit`, else the count text."""
    shown = None if via is None else display_unit(model, via, unit)
    carriers = () if via is None else (printed_designation(model, via, unit=shown),)
    return overview_lifted_text(kind, carriers, count)


def overview_stub_text(model: Model, unit: Id[Unit], stub: OverviewStub) -> str:
    """The text of the line to a stub: its carrier relative to `unit`, else the count text."""
    return overview_end_text(model, unit, stub.kind, stub.via, stub.count)


def overview_stub_lines(stub: OverviewStub) -> tuple[str, ...]:
    """The text lines of a stub's box: the far device, then its port tails when it has any."""
    return (stub.far, stub.ports) if stub.ports else (stub.far,)


def overview_fold_line_text(line: FoldLine) -> str:
    """The text of a folded level's line: its label (cables or `-X3 x 3`), else the count text."""
    return line.label or overview_lifted_text(line.kind, (), line.count)


def overview_fold_stub_text(model: Model, unit: Id[Unit], stub: FoldStub) -> str:
    """The text of the line to a folded stub: its carrier relative to `unit`, else the count."""
    return overview_end_text(model, unit, stub.kind, stub.via, stub.count)


def overview_closed_text(count: int) -> str:
    """The text of a line to a closed fold (`closed_fold`) of `count` connections: `x N`."""
    return f"x {count}"


def closed_fold(stub: FoldStub) -> bool:
    """Whether `stub` folds several connections to one far name that is not a single device."""
    return stub.place is not StubPlace.END and stub.count > 1


def overview_fold_stub_lines(stub: FoldStub) -> tuple[str, ...]:
    """The text lines of a folded stub's box: its far name; a closed fold prints no member list.

    A fold of several members prints its name and count (`Field devices (2)`); any other stub also
    prints the port tails of its members.
    """
    if closed_fold(stub):
        return (stub.far,)
    ports = tuple(dict.fromkeys(m.ports for m in stub.members if m.ports))
    return (stub.far, *ports)


def overview_location_line_text(model: Model, line: LocationLine) -> str:
    """The text of a location line: its cables as `overview_lifted_text` prints them."""
    carriers = tuple(printed_designation(model, cable) for cable in line.cables)
    return overview_lifted_text(OverviewLinkKind.CABLE, carriers, line.count)


def overview_member_text(form: StubText, lines: Sequence[str], carrier: str) -> str:
    """A fold member's row as a stub label, carrier first: `-W11 → +EXT-M1:PE` (O14).

    `lines` is the member's box text (far name, then port tails), `carrier` the cable or wire
    text reaching it. It is `off_stub_line` facing south, so the row reads as the stub does.
    """
    far, *tails = lines
    return off_stub_line(form, carrier, north=False, far=far, ports=tails)
