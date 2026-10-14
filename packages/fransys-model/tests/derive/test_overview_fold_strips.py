"""Strips open at every level that draws or lists them (O5, model-0198): `fold_level(strip=)`."""

import pytest
from fold_builders import SUP_BOX, fold_plant
from overview_builders import item_id

from fransys_model.derive import ItemKind, fold_level
from fransys_model.kernel import SchemaError
from fransys_model.layout import OverviewRef, OverviewRefKind

_STRIPS = OverviewRef(kind=OverviewRefKind.STRIPS)


def _terminals(level) -> list[str]:
    return [b.lines[0] for b in level.boxes if b.item_kind is ItemKind.TERMINAL]


def test_the_strips_level_draws_the_strips_as_boxes_and_ends_wires_at_group_stubs() -> None:
    """The "Terminal strips (n)" box opens as a level: X9 is a box, its wires end at group stubs."""
    model, unit, _ = fold_plant()
    level = fold_level(model, unit, _STRIPS)
    assert level.opened == _STRIPS
    assert [(b.lines[0], b.item_kind) for b in level.boxes] == [("-X9", ItemKind.STRIP)]
    assert sorted(s.far for s in level.stubs) == ["=CTL", "=SUP"]


def test_a_strip_opened_on_the_strips_level_becomes_its_terminal_boxes() -> None:
    """Opening X9 there replaces its box with its terminal; the stubs stay at the terminal."""
    model, unit, _ = fold_plant()
    level = fold_level(model, unit, _STRIPS, strip=item_id("x9"))
    assert _terminals(level) == ["-X9:L:9"]
    assert not [b for b in level.boxes if b.item_kind is ItemKind.STRIP]
    assert sorted(s.far for s in level.stubs) == ["=CTL", "=SUP"]


def test_a_strip_opened_on_a_group_draws_its_terminals_and_no_pass_line() -> None:
    """X1 (held by =SUP) opened: three terminals replace the box and its two lines."""
    model, unit, _ = fold_plant()
    closed = fold_level(model, unit, SUP_BOX)
    level = fold_level(model, unit, SUP_BOX, strip=item_id("x1"))
    assert _terminals(level) == ["-X1:L:1", "-X1:L:2", "-X1:L:3"]
    assert item_id("x1") not in {b.key.item for b in level.boxes}
    assert len(level.lines) > len(closed.lines)


def test_a_passed_through_strip_opened_on_a_group_draws_only_the_terminals_wired_there() -> None:
    """X9 passes K2 to D1 in =SUP: opening it draws its terminal and frees the pass line."""
    model, unit, _ = fold_plant()
    closed = fold_level(model, unit, SUP_BOX)
    level = fold_level(model, unit, SUP_BOX, strip=item_id("x9"))
    assert _terminals(level) == ["-X9:L:9"]
    assert not [line for line in level.lines if line.strip == item_id("x9")]
    assert [line for line in closed.lines if line.strip == item_id("x9")] == []
    assert {s.far for s in level.stubs} == {"=CTL"}


def test_a_strip_opened_on_the_all_devices_level_draws_its_terminals() -> None:
    """The all-devices level lists its strips as it lists X1's terminals when X1 is open."""
    model, unit, _ = fold_plant()
    level = fold_level(model, unit, fold=False, strip=item_id("x1"))
    assert _terminals(level) == ["-X1:L:1", "-X1:L:2", "-X1:L:3"]
    assert {n.strip for n in level.strips} >= {item_id("x2"), item_id("x9")}


def test_a_strip_that_is_not_the_units_is_refused() -> None:
    """An item that is no strip of the unit cannot be opened."""
    model, unit, _ = fold_plant()
    with pytest.raises(SchemaError):
        fold_level(model, unit, SUP_BOX, strip=item_id("p1"))


def test_the_folded_level_opens_no_strip() -> None:
    """The groups view opens no strip: its strips box is the way in."""
    model, unit, _ = fold_plant()
    with pytest.raises(SchemaError, match="opens no strip"):
        fold_level(model, unit, strip=item_id("x1"))


def test_a_strips_level_the_unit_does_not_have_is_refused() -> None:
    """The far unit has no strip outside a group, so it has no strips box to open."""
    model, _, far = fold_plant()
    with pytest.raises(SchemaError):
        fold_level(model, far, _STRIPS)
