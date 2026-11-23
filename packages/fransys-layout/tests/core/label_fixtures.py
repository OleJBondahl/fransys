"""Hand-built label cases on page 1: values written out, no pipeline run.

A body is 16 by 32 with its origin at the centre top, a label is 16 by 8 and the marker is
48 by 16 (Options.marker, MARKER_BOX).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from options_fixtures import core_options
from turn_fixtures import views_of

from fransys_layout.core import (
    AnnexBox,
    Box,
    Facts,
    Options,
    PinRef,
    Placement,
    PlacementProblem,
    Size,
    Sym,
)
from fransys_layout.core.anchors import HELD, ROUTED, Stood, page_keeps
from fransys_layout.core.annex import place_labels
from fransys_layout.core.clearance import Keep
from fransys_layout.core.outputs import (
    Anchored,
    Counts,
    Marker,
    PagePlacement,
    PageRoutes,
    Placed,
    Routes,
    Wire,
)
from fransys_layout.core.values import Finding, RefKind

from .conftest import MARKERS
from .pipeline_fixtures import with_annexes

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence


@dataclass(frozen=True, slots=True)
class LabelCase:
    """The inputs of place_labels, all on page 1; the annexes are el's, one per symbol."""

    placement: Placement
    routes: Routes
    markers: tuple[Marker, ...]
    anchored: tuple[Anchored, ...]
    problem: PlacementProblem

    def run(self, options: Options | None = None) -> tuple[tuple[AnnexBox, ...], tuple[Finding, ...]]:
        """place_labels on this case with the designation annexes `options` gives: the markers and anchors are solids."""
        opts = options or bl_first_options()
        problem = with_annexes(self.problem, opts)
        wires = tuple(w for r in self.routes.pages for w in r.wires)
        page = self.placement.pages[0]
        keeps = page_keeps(page, Stood(self.markers, self.anchored, wires=wires), problem, opts, (*HELD, *ROUTED, "wire"))
        labels, found, _ = place_labels(problem.annexes, {p.sym: p for p in page.placed}, keeps, (1, problem.area, opts.label_gap, opts.label_moves))
        return tuple(labels), tuple(found)


def keeps_of(placed: Mapping[str, Placed], boxes: Sequence[Box] = ()) -> list[Keep]:
    """The ledger of a hand-built page: each placed body and each `boxes` solid, as `page_keeps` gives them."""
    return [*(Keep("", p.body, "body", p.sym) for p in placed.values()), *(Keep("", b, "text", "") for b in boxes)]


def house_options(*, label_gap: int = 8, **fields: Any) -> Options:
    """Options with the house defaults for a label case; `fields` overrides any of them."""
    return core_options(
        marker_boxes=MARKERS,
        label_gap=label_gap,
        **fields,
    )


def bl_first_options() -> Options:
    """BL first and no wire gap: the cases below are built on this order (the KL and KR side
    slots left with text_label_cands, R345; no case here had room for one)."""
    return house_options(corner_order=("BL", "TL", "BR", "TR"), label_gap=0)


def sym(sym_id: str, *, keepout: Box | None = None) -> Sym:
    """A symbol whose keepout is its body unless given."""
    body = Box(-8, -16, 16, 32)
    keepout = keepout or body
    return Sym(
        id=sym_id,
        group=None,
        unit="",
        labels={"": Size(16, 8)},
        pins=(),
        nodes=(),
        views=views_of(body, keepout, body, (), ("R0",)),
    )


def placed(sym_id: str, x: int, y: int) -> Placed:
    """A symbol at (x, y), R0, on page 1."""
    body = Box(x - 8, y - 16, 16, 32)
    return Placed(sym=sym_id, page=1, x=x, y=y, orient="R0", body=body, footprint=body, pin_xy=())


def on_page(at: tuple[tuple[str, int, int], ...], *, wires: tuple[Wire, ...] = ()) -> LabelCase:
    """Plain symbols placed at the given (id, x, y) on page 1, with the given wires."""
    return _case(tuple(sym(sid) for sid, _, _ in at), at, wires=wires)


def _case(
    syms: tuple[Sym, ...],
    at: tuple[tuple[str, int, int], ...],
    *,
    wires: tuple[Wire, ...] = (),
    markers: tuple[Marker, ...] = (),
    anchored: tuple[Anchored, ...] = (),
) -> LabelCase:
    """Page 1 with the symbols placed at the given (id, x, y) and the given wires and markers."""
    placed_all = tuple(placed(sid, x, y) for sid, x, y in at)
    page = PagePlacement(1, placed_all, (), (), (), ())
    routes = Routes((PageRoutes(1, wires, (), Counts(0, 0, 0, 0), (), (), ()),))
    problem = PlacementProblem(Size(400, 300), syms, (), facts=Facts(far_ends=()))
    return LabelCase(Placement((page,)), routes, markers, anchored, problem)


def lone() -> LabelCase:
    """One symbol at (88, 96): body Box(80, 80, 16, 32); first candidate Box(80, 112, 16, 8)."""
    return _case((sym("S1"),), (("S1", 88, 96),))


def under_wire() -> LabelCase:
    """lone() with a horizontal wire at y 116 from x 64 to 112, across the first candidate."""
    wire = Wire("n1", 1, ((64, 116), (112, 116)), "straight")
    return _case((sym("S1"),), (("S1", 88, 96),), wires=(wire,))


def colliding_neighbours() -> LabelCase:
    """S2 sits directly above S1, so S2's first (BL) candidate lies on S1's body.

    S1 at (88, 96) has body Box(80, 80, 16, 32) and first candidate Box(80, 112, 16, 8).
    S2 at (88, 64) has body Box(80, 48, 16, 32): the bodies touch at y 80 and do not overlap.
    """
    return _case((sym("S1"), sym("S2")), (("S1", 88, 96), ("S2", 88, 64)))


def dense() -> LabelCase:
    """Three symbols in a row at y 96 (bodies x 80, 132, 184) and an anchored outline covering the page."""
    syms = (sym("S1"), sym("S2"), sym("S3"))
    at = (("S1", 88, 96), ("S2", 140, 96), ("S3", 192, 96))
    cover = Anchored("S1", "p", 1, 0, 0, "R0", Box(0, 0, 400, 300), (0, 0), ((0, 0), (0, 0)))
    return _case(syms, at, anchored=(cover,))


def marker_over_candidate() -> LabelCase:
    """lone() plus a COPY marker at (88, 116): its box overlaps the first candidate."""
    marker = Marker("n1", RefKind.COPY, 1, 88, 116, PinRef("S1", "p"))
    return _case((sym("S1"),), (("S1", 88, 96),), markers=(marker,))
