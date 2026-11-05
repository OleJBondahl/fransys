"""The fold: a view's footprint also holds the page's hangings at their pins (H4, layout-0395)."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Any

from fransys_layout.core import Box, PinRef
from fransys_layout.core.anchors import folded
from fransys_layout.core.hangings import Hanging

from .cut_fixtures import free

if TYPE_CHECKING:
    from fransys_layout.core import Orientation

PIN_N = PinRef("H", "n")
TAG = Hanging(PIN_N, "N", Box(-6, -18, 12, 18), "tag")


def _by_orient(h: Hanging) -> dict[tuple[str, str, Orientation], tuple[Hanging, ...]]:
    return {("H", "n", "R0"): (h,)}


def test_a_page_with_no_hangings_returns_the_symbols_unchanged() -> None:
    syms = {"H": free("H")}
    assert folded(syms, {}) == syms


def test_a_tag_hanging_grows_the_footprint_to_its_box_at_the_pin() -> None:
    sym = free("H")
    view = folded({"H": sym}, _by_orient(TAG))["H"].views["R0"]
    pin = sym.views["R0"].pins[0]
    box = Box(TAG.box_rel.x + pin.dx, TAG.box_rel.y + pin.dy, 12, 18)
    assert view.footprint.y <= box.y
    assert view.footprint.x <= box.x
    assert view.footprint.x + view.footprint.w >= box.x + box.w
    assert view.footprint != sym.views["R0"].footprint


def test_the_fold_leaves_body_and_keepout_and_the_other_views_alone() -> None:
    sym = free("H")
    out = folded({"H": sym}, _by_orient(TAG))["H"]
    assert out.views["R0"].body == sym.views["R0"].body
    assert out.views["R0"].keepout == sym.views["R0"].keepout
    assert {o: v for o, v in out.views.items() if o != "R0"} == {o: v for o, v in sym.views.items() if o != "R0"}


def test_an_anchor_hanging_adds_nothing_because_reserved_joined_it_already() -> None:
    sym = free("H")
    anchor = TAG._replace(kind="anchor")
    assert folded({"H": sym}, _by_orient(anchor)) == {"H": sym}


def test_a_row_footprint_holds_the_box_too() -> None:
    sym = free("H")
    row = Box(-8, -16, 16, 32)
    sym = replace(sym, views={"R0": replace(sym.views["R0"], row_footprint=row)})
    view = folded({"H": sym}, _by_orient(TAG))["H"].views["R0"]
    assert view.row_footprint is not None
    assert view.row_footprint.y < row.y


def test_phase_two_staggers_the_flags_of_a_row_across_symbols_where_phase_one_cannot() -> None:
    """R565: two symbols' tags that overlap in x stand one box apart once x is known."""
    from types import SimpleNamespace

    from fransys_layout.core.outputs import PinXY

    syms = {"A": free("A"), "B": free("B")}
    hangings: dict[tuple[str, str, Orientation], tuple[Hanging, ...]] = {
        ("A", "n", "R0"): (Hanging(PinRef("A", "n"), "N", TAG.box_rel, "tag"),),
        ("B", "n", "R0"): (Hanging(PinRef("B", "n"), "N", TAG.box_rel, "tag"),),
    }
    one = folded(syms, hangings)
    placed: Any = {s: SimpleNamespace(orient="R0", pin_xy=(PinXY("n", 100, 50),)) for s in syms}
    two = folded(syms, hangings, (), placed, {("A", "n"): 0, ("B", "n"): 0})
    top = {s: v[s].views["R0"].footprint.y for s, v in (("A", one), ("B", one))}
    after = {s: two[s].views["R0"].footprint.y for s in syms}
    assert top["A"] == top["B"]
    assert sorted(after.values()) == [top["A"] - TAG.box_rel.h, top["A"]]
