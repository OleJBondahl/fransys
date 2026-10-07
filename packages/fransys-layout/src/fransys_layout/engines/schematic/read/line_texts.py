"""What a harness line prints, measured: its designation (HL3) and a leaving line's stub (HL18).

Derive prints both texts; layout only measures them, as render prints them.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from fransys_layout.geometry import Facing, text_width
from fransys_layout.stages.line_shapes import LineStub
from fransys_layout.stages.references.marker_boxes import stub_size
from fransys_layout.stages.texts.candidates import Candidate, box_of, stub_anchor
from fransys_model.derive import line_designation, line_stub_line, printed_designation
from fransys_model.derive.drawing_text import stub_far_end
from fransys_model.vocab.tables import conductors, ports

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fransys_layout.stages.line_draw import Stub
    from fransys_layout.stages.types import Profile
    from fransys_model.kernel import Id, Model

    from .harness_lines import LineRead, LineReads


@dataclass(frozen=True)
class LineTexts:
    """Each line's designation per branch and one port per end, read once."""

    model: Model
    designation: dict[tuple[Id[Any], int], str]
    port: dict[tuple[Id[Any], int], Id[Any]]

    def size(self, owner: Id[Any], branch: int, profile: Profile) -> tuple[int, int]:
        """The designation's `(width, height)` at the page's text height."""
        text = self.designation[owner, branch]
        return text_width(text, height=profile.text_height), profile.text_height


def line_texts(model: Model, lines: LineReads) -> LineTexts:
    """Every line's designations and end ports (`derive.line_designation`, the ends row).

    A plug's end names the connector it mates, as a stub names the device beyond (C21).
    """
    of: dict[Id[Any], list[Id[Any]]] = {}
    for one in sorted(ports(model).values(), key=lambda one: one.id):
        of.setdefault(one.function, []).append(one.id)
    wires = conductors(model)
    designation: dict[tuple[Id[Any], int], str] = {}
    port: dict[tuple[Id[Any], int], Id[Any]] = {}
    for line in lines.lines:
        ends = {p for c in line.conductors for p in (wires[c].a, wires[c].b)}
        for end in line.ends:
            designation[line.owner, end.branch] = line_designation(
                model, line.owner, end.branch, unit=line.unit
            )
            plug = sorted(p for p in of.get(end.plug, ()) if p in ends)
            mine = end.ports or of.get(end.mates, ()) or plug
            if mine:
                port[line.owner, end.branch] = mine[0]
    return LineTexts(model, designation, port)


def stub_box(
    texts: LineTexts,
    line: LineRead,
    stub: Stub,
    sheet: tuple[tuple[int, int], Id[Any] | None],
    profile: Profile,
) -> LineStub:
    """HL18: the leaving line's one stub, its text `derive.line_stub_line` measured (C1).

    `sheet` is the page and its drawing set's unit, which the carrier prints relative to.
    """
    page, unit = sheet
    near, far = texts.port[line.owner, stub.near], texts.port[line.owner, stub.far]
    text = _stub_text(texts, line.owner, (near, far), unit, north=stub.end.facing is Facing.N)
    width, height = stub_size(text, profile)
    at = stub.end.at
    return LineStub(
        harness=line.owner,
        branch=stub.near,
        drawing_set=page[0],
        page=page[1],
        port=near,
        far=far,
        at=at,
        facing=stub.end.facing,
        box=box_of(Candidate(side=stub.end.facing, offset=0), stub_anchor(at), (width, height)),
    )


def _stub_text(
    texts: LineTexts,
    owner: Id[Any],
    ends: tuple[Id[Any], Id[Any]],
    unit: Id[Any] | None,
    *,
    north: bool,
) -> str:
    """`derive.line_stub_line` for a stub at port `ends[0]` naming the far port `ends[1]`."""
    head, _ = stub_far_end(texts.model, ends[1], ends[0], unit=unit)
    cable = printed_designation(texts.model, owner, unit=unit)
    return line_stub_line(cable, north=north, far=head)


def widest_stub(texts: LineTexts, line: LineRead, unit: Id[Any] | None, profile: Profile) -> int:
    """The widest stub `line` may end in on a sheet of `unit`: any end's port naming another's."""
    ports = [
        texts.port[line.owner, end.branch]
        for end in line.ends
        if (line.owner, end.branch) in texts.port
    ]
    return max(
        (
            stub_size(_stub_text(texts, line.owner, (near, far), unit, north=north), profile)[0]
            for near in ports
            for far in ports
            if near != far
            for north in (True, False)
        ),
        default=0,
    )


def marker_keepouts(
    model: Model, markers: Sequence[Any]
) -> tuple[tuple[tuple[int, int], Id[Any], Any], ...]:
    """Each marker's box by page, owned by its port's function: a line may start beside it."""
    table = ports(model)
    return tuple(((m.drawing_set, m.page), table[m.port].function, m.box) for m in markers)
