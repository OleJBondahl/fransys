"""Hand-built wire-label cases on page 1, in G: values written out, no pipeline run.

The label is 24 by 8. A page grid comes from `page_grid`, so a trunk is marked as stage 8b marks it.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from options_fixtures import core_options

from fransys_layout.core import Facts, Net, Placement, PlacementProblem, Size
from fransys_layout.core.outputs import Counts, PagePlacement, PageRoutes, Routes, Wire
from fransys_layout.core.text_label_grid import page_grid
from fransys_layout.core.values import Box

from .conftest import MARKER

if TYPE_CHECKING:
    from fransys_layout.core.occupancy import Occupancy

LABEL = Size(24, 8)
AREA = Size(400, 300)
OPTIONS = core_options(
    marker=MARKER,
    flip_turn="R180",
    tag_stagger=True,
    label_gap=8,
    parallel_pitch=48,
    driver_first=True,
    arrow_sides=("E", "W"),
)


def grid(wires: tuple[Wire, ...] = (), boxes: tuple[Box, ...] = (), step: int = 8) -> Occupancy:
    """The page grid of page 1 with the wires (a trunk lanes wide) and the boxes marked."""
    page = PagePlacement(1, (), (), (), (), ())
    return page_grid(page, wires, boxes, AREA, replace(OPTIONS, wiring_grid=step))


def wire(points: tuple[tuple[int, int], ...], net: str = "n1") -> Wire:
    return Wire(net, 1, points, "straight")


def lone() -> Wire:
    """A vertical wire of 48 G at x 96, y 64 to 112; the label's first side is E."""
    return wire(((96, 64), (96, 112)))


def east_blocked() -> tuple[Box, ...]:
    """A footprint across every E candidate of lone()."""
    return (Box(104, 64, 40, 48),)


def walled() -> tuple[Box, ...]:
    """A footprint on each side of lone(): no side is free."""
    return (Box(104, 0, 100, 300), Box(40, 0, 56, 300))


def bent() -> Wire:
    """A horizontal run of 20 G (shorter than the label) and a vertical run of 16 G."""
    return wire(((40, 100), (60, 100), (60, 116)))


def trunk(lanes: int = 3) -> tuple[Wire, ...]:
    """A vertical trunk of 48 G at x 96, y 64 to 112: one wire per lane, a grid step apart to +x."""
    return tuple(wire(((96 + 8 * k, 64), (96 + 8 * k, 112))) for k in range(lanes))


def case(
    wires: tuple[Wire, ...], nets: tuple[Net, ...]
) -> tuple[Placement, Routes, PlacementProblem]:
    """Page 1 with no symbol, the wires, and the nets."""
    placement = Placement((PagePlacement(1, (), (), (), (), ()),))
    routes = Routes((PageRoutes(1, wires, (), Counts(0, 0, 0, 0, 0)),))
    return (
        placement,
        routes,
        PlacementProblem(AREA, (), nets, facts=Facts()),
    )
