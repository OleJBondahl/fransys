"""The text of an off stub and of a leaving line's stub (decision model-0032)."""

from typing import cast
lazy from collections.abc import Iterable, Sequence

from fransys_model.derive.designation import (
    printed_designation,
)
from fransys_model.derive.house_settings import stub_text_of
from fransys_model.derive.line_fact import draws_as_line
from fransys_model.derive.location_text import stub_far_end
from fransys_model.layout import (
    DrawingSet,
    LinkMarker,
    Page,
    Side,
    StarKind,
    StubText,
    layout_of,
)
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Item, Port, Unit


def off_stub_line(
    form: StubText, cable: str, *, north: bool, far: str, ports: Iterable[str]
) -> str:
    """One off stub's text, `-W3 → +EXT-M1:U1 U2`: what layout measures and derive prints.

    `cable` is the carrier's `-designation` (empty for none), `far` the far device's product
    designation and `ports` the far end's port tails, each with or without its leading `:`,
    listed in the order given. The arrow points up (`form.arrow_in`) for a stub facing north,
    else `form.arrow_out`; `form` is the `[stub]` record.
    """
    arrow = form.arrow_in if north else form.arrow_out
    tails = form.port_join.join(port.removeprefix(":") for port in ports if port)
    joined = f"{far}{form.port_sep}{tails}" if tails else far
    return " ".join(part for part in (cable, arrow, joined) if part)


def line_stub_line(
    form: StubText, line: str, *, north: bool, far: Sequence[tuple[str, str]]
) -> str:
    """A leaving line's single stub, `-W3 → +EXT-M1 p2:4A, +EXT-M2 p2:5C`: line, arrow, far devices.

    `far` is each far device with where it is drawn in the stub's drawing set, `position_text`'s
    form, or "" for none. No place at all keeps the first device alone, the text without places.
    The arrow is `form`'s: up for a stub facing north, else the other.
    """
    listed = far if any(place for _, place in far) else far[:1]
    devices = ", ".join(f"{device} {place}" if place else device for device, place in listed)
    return off_stub_line(form, line, north=north, far=devices, ports=())


def _stub_end_of(model: Model, marker: LinkMarker, unit: Id[Unit] | None) -> tuple[str, str]:
    """`stub_far_end` of an off stub `marker`'s far port, printed in `unit`'s document."""
    return stub_far_end(model, cast("Id[Port]", marker.far), marker.port, unit=unit)


def _cable_and_head(
    model: Model, unit: Id[Unit] | None, carrier: Id[Item] | None, far: Id[Port], port: Id[Port]
) -> tuple[str, str, str]:
    """The printed carrier (`""` for none), the far device and the far port's tail in `unit`."""
    cable = "" if carrier is None else printed_designation(model, carrier, unit=unit)
    head, tail = stub_far_end(model, far, port, unit=unit)
    return cable, head, tail


def stub_text_at(
    model: Model,
    unit: Id[Unit] | None,
    ends: tuple[Id[Port], Id[Port], Id[Item] | None],
    *,
    north: bool,
) -> str:
    """The text of a lone off stub before it is placed: what `off_stub_text` prints for it.

    `ends` is `stub_far`'s `(near, far, carrier)`. The stub stands in no run and no line end is
    drawn yet (layout sizes its box from this text).
    """
    port, far, carrier = ends
    cable, head, tail = _cable_and_head(model, unit, carrier, far, port)
    form = stub_text_of(model)
    if carrier is not None and draws_as_line(model, carrier):
        return line_stub_line(form, cable, north=north, far=[(head, "")])
    return off_stub_line(form, cable, north=north, far=head, ports=(tail,))


def off_stub_text(model: Model, marker: LinkMarker) -> str:
    """What an off stub says: `-W3 → +EXT-M1:U1 U2`, cable, arrow, far device and its ports.

    A carrier that `draws_as_line` prints `-W14 → -M1`, no ports. Layout sizes the box from it,
    render prints it; `←` faces `Side.N`, else `→`. Raises `ValueError` without `far`.
    """
    if marker.star is not StarKind.OFF or marker.far is None:
        msg = "off_stub_text needs an off stub (star OFF) with a far port"
        raise ValueError(msg)
    unit = layout_of(model, DrawingSet)[layout_of(model, Page)[marker.page].drawing_set].unit
    cable, head, _ = _cable_and_head(model, unit, marker.carrier, marker.far, marker.port)
    form = stub_text_of(model)
    if marker.carrier is not None and draws_as_line(model, marker.carrier):
        return line_stub_line(form, cable, north=marker.facing is Side.N, far=[(head, "")])
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
    return off_stub_line(form, cable, north=marker.facing is Side.N, far=head, ports=tails)
