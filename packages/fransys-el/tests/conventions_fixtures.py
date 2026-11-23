"""The house conventions a placement test builds: `layout.toml`'s table, read as the facade does."""

import tomllib
from dataclasses import replace
from pathlib import Path

from fransys_el import house_conventions
from fransys_el.placement_markers import facing_views, marker_boxes_value
from fransys_el.placement_options import options
from sheet_formats import a3
lazy from fransys_el.placement_options import Conventions

import fransys_layout
from electrical_symbols import LIBRARY
from fransys_layout.core import Options, PinRef, PlacementProblem

SHEET = a3()  # the A3 sheet
LAYOUT = tomllib.loads((Path(fransys_layout.__file__).parent / "layout.toml").read_text(encoding="utf-8"))["layout"]


def house() -> Conventions:
    """The house conventions of the stock library and `layout.toml`."""
    return house_conventions(LAYOUT, LIBRARY, text_height=8, sheet=SHEET)


def unwired(problem: PlacementProblem) -> PlacementProblem:
    """`problem` with no wire drawn: each unit boundary pin has one required conductor to a pin outside it, so the cut stubs it (R407)."""
    edge = {p for u in problem.facts.units for p in u.boundary}
    out = tuple((p, PinRef("out", f"{p.sym}.{p.pin}")) for p in sorted(edge, key=lambda p: (p.sym, p.pin)))
    return replace(problem, facts=replace(problem.facts, far_ends=out, groups=out))


def drawn_options(model, kit, problem: PlacementProblem, conventions: Conventions) -> Options:
    """The core options `lay_out` solves `problem` with: the conventions' options and the marker boxes fitted to its pins (SB4)."""
    pins = [PinRef(s.id, p.id) for s in problem.symbols for p in s.pins]
    boxes, lines, table = marker_boxes_value(model, kit, (None, LIBRARY), pins)
    turned, above, below = facing_views()
    return replace(
        options(conventions, LIBRARY),
        marker_boxes=boxes,
        stub_lines=lines,
        stub_table=table,
        marker_vertical=turned,
        marker_above=above,
        marker_below=below,
    )
