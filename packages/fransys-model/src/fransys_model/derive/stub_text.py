"""The text of an off stub and of a leaving line's stub (decision model-0032)."""

from collections import defaultdict
from typing import cast
lazy from collections.abc import Iterable, Sequence

from fransys_model.derive.designation import (
    printed_designation,
)
from fransys_model.derive.frame_position import place_text
from fransys_model.derive.line_fact import draws_as_line
from fransys_model.derive.location_text import stub_far_end
from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, digest_cached
from fransys_model.layout import (
    DrawingSet,
    LinkMarker,
    Page,
    Side,
    StarKind,
    StubEnd,
    layout_of,
)
lazy from fransys_model.vocab.core import Port, Unit


def off_stub_line(cable: str, *, north: bool, far: str, ports: Iterable[str]) -> str:
    """One off stub's text, `-W3 → +EXT-M1:U1 U2`: what layout measures and derive prints.

    `cable` is the carrier's `-designation` (empty for none), `far` the far device's product
    designation and `ports` the far end's port tails, each with or without its leading `:`,
    listed in the order given. The arrow points up (`←`) for a stub facing north, else `→`.
    """
    arrow = "←" if north else "→"
    tails = " ".join(port.removeprefix(":") for port in ports if port)
    return " ".join(part for part in (cable, arrow, f"{far}:{tails}" if tails else far) if part)


def line_stub_line(line: str, *, north: bool, far: Sequence[tuple[str, str]]) -> str:
    """A leaving line's single stub, `-W3 → +EXT-M1 p2:4A, +EXT-M2 p2:5C`: line, arrow, far devices.

    `far` is each far device with where it is drawn in the stub's drawing set, `position_text`'s
    form, or "" for none. No place at all keeps the first device alone, the text without places.
    The arrow points up (`←`) for a stub facing north, else `→`.
    """
    listed = far if any(place for _, place in far) else far[:1]
    devices = ", ".join(f"{device} {place}" if place else device for device, place in listed)
    return off_stub_line(line, north=north, far=devices, ports=())


def _stub_end_of(model: Model, marker: LinkMarker, unit: Id[Unit] | None) -> tuple[str, str]:
    """`stub_far_end` of an off stub `marker`'s far port, printed in `unit`'s document."""
    return stub_far_end(model, cast("Id[Port]", marker.far), marker.port, unit=unit)


@digest_cached(DIGEST_CACHE_SIZE)
def _stub_ends(model: Model) -> dict[Id[LinkMarker], list[StubEnd]]:
    found: dict[Id[LinkMarker], list[StubEnd]] = defaultdict(list)
    for end in sorted(layout_of(model, StubEnd).values(), key=lambda e: (e.marker, e.index)):
        found[end.marker].append(end)
    return found


def _line_stub_far(
    model: Model, marker: LinkMarker, unit: Id[Unit] | None, head: str
) -> list[tuple[str, str]]:
    """A line stub's far devices with their places, from its `StubEnd` records.

    A stub with none keeps its `far` port's device alone (a hand-made marker, an old model).
    """
    ends = _stub_ends(model).get(marker.id)
    if not ends:
        return [(head, "")]
    pages = layout_of(model, Page)
    return [
        (
            stub_far_end(model, end.port, marker.port, unit=unit)[0],
            ""
            if end.page is None
            else place_text(model, pages[marker.page], pages[end.page], end.x, end.y),
        )
        for end in ends
    ]


def off_stub_text(model: Model, marker: LinkMarker) -> str:
    """What an off stub says: `-W3 → +EXT-M1:U1 U2`, cable, arrow, far device and its ports.

    A carrier that `draws_as_line` prints `-W14 → -M1`, no ports. Layout sizes the box from it,
    render prints it; `←` faces `Side.N`, else `→`. Raises `ValueError` without `far`.
    """
    if marker.star is not StarKind.OFF or marker.far is None:
        msg = "off_stub_text needs an off stub (star OFF) with a far port"
        raise ValueError(msg)
    unit = layout_of(model, DrawingSet)[layout_of(model, Page)[marker.page].drawing_set].unit
    cable = "" if marker.carrier is None else printed_designation(model, marker.carrier, unit=unit)
    head, _ = stub_far_end(model, marker.far, marker.port, unit=unit)
    if marker.carrier is not None and draws_as_line(model, marker.carrier):
        far = _line_stub_far(model, marker, unit, head)
        return line_stub_line(cable, north=marker.facing is Side.N, far=far)
    run = [marker]
    if marker.box_x is not None:
        run = sorted(
            (
                other
                for other in layout_of(model, LinkMarker).values()
                if other.star is StarKind.OFF
                and other.page == marker.page
                and other.box_x == marker.box_x
                and other.y == marker.y
                and other.carrier == marker.carrier
                and _stub_end_of(model, other, unit)[0] == head
            ),
            key=lambda other: (other.x, other.id),
        )
    tails = (_stub_end_of(model, other, unit)[1] for other in run)
    return off_stub_line(cable, north=marker.facing is Side.N, far=head, ports=tails)
