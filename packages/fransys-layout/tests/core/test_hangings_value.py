"""The Hanging value and its kind map (layout-0395)."""

from __future__ import annotations

import pytest

from fransys_layout.core.hangings import KEEP_KIND, Hanging, hanging_keep
from fransys_layout.core.values import Box, PinRef

FINE = ("tag", "arrow", "copy", "stub", "star", "lead", "flag", "anchor", "dot", "wire")
COARSE = {"lead": "lead", "anchor": "anchor", "dot": "dot", "wire": "wire"}


def _hanging(kind: str, box: Box | None = None) -> Hanging:
    box = box or Box(-2, 3, 4, 5)
    return Hanging(PinRef("S1", "1"), "S", box, kind)


def test_every_fine_kind_maps_to_its_coarse_kind() -> None:
    assert set(KEEP_KIND) == set(FINE)
    for kind in FINE:
        keep = hanging_keep(_hanging(kind), (0, 0), "S1", None)
        assert keep.kind == COARSE.get(kind, "marker"), kind


def test_keep_box_is_shifted_to_the_pin_point_with_absolute_y() -> None:
    keep = hanging_keep(_hanging("tag"), (10, 20), "S1", "N1")
    assert keep.box == Box(8, 23, 4, 5)
    assert (keep.node, keep.owner, keep.net) == ("", "S1", "N1")


def test_two_hangings_on_one_pin_give_two_keeps() -> None:
    first, second = _hanging("arrow"), _hanging("stub", Box(0, 0, 1, 1))
    keeps = [hanging_keep(h, (5, 5), "S1", None) for h in (first, second)]
    assert [k.box for k in keeps] == [Box(3, 8, 4, 5), Box(5, 5, 1, 1)]


def test_an_unknown_kind_raises() -> None:
    with pytest.raises(KeyError):
        hanging_keep(_hanging("balloon"), (0, 0), "S1", None)
