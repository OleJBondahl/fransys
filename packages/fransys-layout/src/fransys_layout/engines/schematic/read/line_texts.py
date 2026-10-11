"""What a harness line prints, measured: its designation (HL3) and a leaving line's stub (HL18).

Derive prints both texts; layout only measures them, as render prints them.
"""

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any

from fransys_layout.geometry import Box, Facing, text_width
from fransys_layout.stages.content import content_box
from fransys_layout.stages.line_shapes import FarEnd, LineStub
from fransys_layout.stages.references.marker_boxes import stub_size
from fransys_layout.stages.texts.candidates import Candidate, box_of, stub_anchor
from fransys_model.derive import line_designation, line_stub_line, printed_designation
from fransys_model.derive.drawing_text import (
    frame_column,
    frame_row,
    partner_position_text,
    stub_far_end,
)
from fransys_model.vocab.tables import conductors, ports

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fransys_layout.stages.line_draw import Stub
    from fransys_layout.stages.types import Profile, SheetFormat
    from fransys_model.kernel import Id, Model

    from .harness_lines import LineRead, LineReads
    from .stub_places import Page, Spots

    type Sheet = tuple[Page, Id[Any] | None, Sequence[int]]  # page, unit, ends off the page


@dataclass(frozen=True)
class LineTexts:
    """Each line's designation per branch and one port per end, read once."""

    model: Model
    designation: dict[tuple[Id[Any], int], str]
    port: dict[tuple[Id[Any], int], Id[Any]]
    spots: dict[tuple[Id[Any], int], Spots] = field(default_factory=dict)  # where each end draws
    sheet: Any = None  # the frame its places are read in

    def size(self, owner: Id[Any], branch: int, profile: Profile) -> tuple[int, int]:
        """The designation's `(width, height)` at the page's text height."""
        text = self.designation[owner, branch]
        return text_width(text, height=profile.text_height), profile.text_height

    def spot(self, owner: Id[Any], branch: int, page: Page) -> tuple[int, int, int] | None:
        """The end's lowest page in `page`'s drawing set and its `(number, x, y)` there, if any."""
        here = {
            at: xy for at, xy in self.spots.get((owner, branch), {}).items() if at[0] == page[0]
        }
        if not here:
            return None
        (_, number), (x, y) = min(here.items())
        return number, x, y

    def place(self, owner: Id[Any], branch: int, page: Page) -> str:
        """Where the end is drawn in `page`'s drawing set, as render prints it ("" for nowhere)."""
        found = self.spot(owner, branch, page)
        if found is None:
            return ""
        number, x, y = found
        column = frame_column(self.sheet.content_width, self.sheet.frame_columns, x)
        row = frame_row(self.sheet.content_height, self.sheet.frame_rows, y)
        return partner_position_text((*page, ()), (page[0], number, ()), column, row)


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
    texts: LineTexts, line: LineRead, stub: Stub, sheet: Sheet, profile: Profile
) -> LineStub:
    """HL18: the leaving line's one stub, its text `derive.line_stub_line` measured (C1).

    `sheet` is the page, its drawing set's unit (the carrier prints relative to it) and every end
    off the page: with none the stub names its `far` end alone (R6).
    """
    page, _, absent = sheet
    near, far = texts.port[line.owner, stub.near], texts.port[line.owner, stub.far]
    north = stub.end.facing is Facing.N
    fars = absent or (stub.far,)
    text = _stub_text(texts, (line.owner, near), fars, sheet, north=north)
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
        ends=tuple(_far_end(texts, line.owner, b, page) for b in fars),
        box=_inside(
            box_of(Candidate(side=stub.end.facing, offset=0), stub_anchor(at), (width, height)),
            texts.sheet,
        ),
    )


def _inside(box: Box, sheet: SheetFormat | None) -> Box:
    """`box` slid sideways, away from the stub's side, until it lies in the content box."""
    if sheet is None:
        return box
    content = content_box(sheet)
    x = max(content.x, min(box.x, content.x + content.width - box.width))
    return replace(box, x=x)


def _far_end(texts: LineTexts, owner: Id[Any], branch: int, page: Page) -> FarEnd:
    """One far end of a stub: its port and where it is drawn in the stub's drawing set."""
    found = texts.spot(owner, branch, page)
    port = texts.port[owner, branch]
    if found is None:
        return FarEnd(port=port, page=None, x=0, y=0)
    return FarEnd(port=port, page=found[0], x=found[1], y=found[2])


def _stub_text(
    texts: LineTexts, at: tuple[Id[Any], Id[Any]], fars: Sequence[int], sheet: Sheet, *, north: bool
) -> str:
    """`derive.line_stub_line` for a stub at port `near` naming the `fars` ends and their places."""
    (owner, near), (page, unit, _) = at, sheet
    cable = printed_designation(texts.model, owner, unit=unit)
    named = [
        (
            stub_far_end(texts.model, texts.port[owner, b], near, unit=unit)[0],
            texts.place(owner, b, page),
        )
        for b in fars
    ]
    return line_stub_line(cable, north=north, far=named)


def widest_stub(
    texts: LineTexts,
    line: LineRead,
    sheet: Sheet,
    profile: Profile,
) -> int:
    """The widest stub `line` may end in on `sheet`: any end naming the ends off it, or another."""
    absent = sheet[2]
    branches = [end.branch for end in line.ends if (line.owner, end.branch) in texts.port]
    return max(
        (
            stub_size(
                _stub_text(
                    texts, (line.owner, texts.port[line.owner, near]), fars, sheet, north=north
                ),
                profile,
            )[0]
            for near in branches
            for fars in ([absent] if absent else [(b,) for b in branches if b != near])
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
