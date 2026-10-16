"""Hand-built label cases on page 1: values written out, no pipeline run.

A body is 16 by 32 with its origin at the centre top, a label is 16 by 8 and the marker is
48 by 16 (Options.marker, MARKER_BOX).
Options(marker=MARKER_BOX) applies. Symbol (x, y) has body Box(x-8, y-16, 16, 32).
"""

from __future__ import annotations

from dataclasses import dataclass

from fransys_layout.core import Box, Options, PinRef, Placement, PlacementProblem, Size, Sym
from fransys_layout.core.outputs import (
    Annotations,
    Counts,
    Label,
    Marker,
    PagePlacement,
    PageRoutes,
    Placed,
    Routes,
    Table,
    Wire,
)
from fransys_layout.core.values import Finding, RefKind

from .conftest import MARKER_BOX


@dataclass(frozen=True, slots=True)
class LabelCase:
    """The inputs of label_pages, all on page 1."""

    placement: Placement
    routes: Routes
    markers: tuple[Marker, ...]
    tables: tuple[Table, ...]
    problem: PlacementProblem

    def run(self, options: Options | None = None) -> tuple[tuple[Label, ...], tuple[Finding, ...]]:
        """label_pages on this case; imported late because it lands with stage 8."""
        from fransys_layout.core.text_labels import label_pages

        return label_pages(
            self.placement,
            self.routes,
            Annotations(markers=self.markers, tables=self.tables),
            self.problem,
            options or Options(marker=MARKER_BOX),
        )


def sym(sym_id: str, *, keepout: Box | None = None) -> Sym:
    """A symbol whose keepout is its body unless given."""
    body = Box(-8, -16, 16, 32)
    return Sym(
        id=sym_id,
        group=None,
        unit="",
        label=Size(16, 8),
        body=body,
        keepout=keepout or body,
        footprint=body,
        pins=(),
        nodes=(),
        orientations=frozenset({"R0"}),
    )


def placed(sym_id: str, x: int, y: int) -> Placed:
    """A symbol at (x, y), R0, on page 1."""
    body = Box(x - 8, y - 16, 16, 32)
    return Placed(sym=sym_id, page=1, x=x, y=y, orient="R0", body=body, footprint=body, pin_xy=())


def _case(
    syms: tuple[Sym, ...],
    at: tuple[tuple[str, int, int], ...],
    *,
    wires: tuple[Wire, ...] = (),
    markers: tuple[Marker, ...] = (),
    tables: tuple[Table, ...] = (),
) -> LabelCase:
    """Page 1 with the symbols placed at the given (id, x, y) and the given wires and markers."""
    placed_all = tuple(placed(sid, x, y) for sid, x, y in at)
    page = PagePlacement(1, placed_all, (), (), (), ())
    routes = Routes((PageRoutes(1, wires, (), Counts(0, 0, 0, 0, 0)),))
    problem = PlacementProblem(Size(400, 300), syms, ())
    return LabelCase(Placement((page,)), routes, markers, tables, problem)


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
    S2's first candidate is Box(80, 80, 16, 8), inside S1's body, so it is not free.
    Two BL labels of equal size cannot overlap without their bodies overlapping, so a label
    collision needs another shape; this case tests the move off a body.
    """
    return _case((sym("S1"), sym("S2")), (("S1", 88, 96), ("S2", 88, 64)))


def dense() -> LabelCase:
    """Three symbols in a row at y 96 (bodies x 80, 132, 184) and a table covering the page."""
    syms = (sym("S1"), sym("S2"), sym("S3"))
    at = (("S1", 88, 96), ("S2", 140, 96), ("S3", 192, 96))
    table = Table("K1", 1, (), Box(0, 0, 400, 300), 0)
    return _case(syms, at, tables=(table,))


def with_slot() -> LabelCase:
    """One symbol at (88, 96) with keepout Box(-24, -16, 48, 32): a left and a right slot."""
    slot_sym = sym("S1", keepout=Box(-24, -16, 48, 32))
    return _case((slot_sym,), (("S1", 88, 96),))


def marker_over_candidate() -> LabelCase:
    """lone() plus a COPY marker at (88, 116): its box overlaps the first candidate."""
    marker = Marker("n1", RefKind.COPY, 1, "a", 88, 116, PinRef("S1", "p"))
    return _case((sym("S1"),), (("S1", 88, 96),), markers=(marker,))
