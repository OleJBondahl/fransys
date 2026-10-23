"""`link_fit`: the arrow's box is sized for the widest line the pages can print (R350)."""

import tempfile
from pathlib import Path
from typing import NamedTuple

import fransys as fr
from fransys_el.placement_ids import symbol_ids
from fransys_el.placement_sets import drawing_scopes
from fransys_el.placement_widest import link_fit
from ring_cases import box_kit, channels_model

from electrical_symbols import LIBRARY


def _width(count: int) -> int:
    model = channels_model(count)
    return link_fit(model, box_kit(model), LIBRARY, None)["R0"].w


def test_a_two_digit_page_number_widens_the_box_over_a_one_digit_one() -> None:
    """The bound is the digit count of the symbol count: ten symbols print `#10-p10:...`."""
    small, large = channels_model(1), channels_model(21)
    assert len(symbol_ids(small, box_kit(small))) < 10 <= len(symbol_ids(large, box_kit(large)))
    assert _width(1) < _width(21)  # 60 and 74 G


def test_the_box_is_never_narrower_than_the_plain_marker() -> None:
    assert _width(1) >= 48


def _star_model(*, parent_lamps: int):
    """A three-lamp unit, alone or inside a parent that draws `parent_lamps` lamps of its own."""

    class _Io(NamedTuple):
        lamp: object

    @fr.unit("demo-star", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
    def star(u: fr.Design) -> _Io:
        lamp, second, third = (u.device(f"P{n}", "DEMO-LAMP-24") for n in (2, 3, 4))
        u.detail.wire(lamp["1"], second["1"], wire=("WH", 0.75))
        u.detail.wire(lamp["1"], third["1"], wire=("WH", 0.75))
        return _Io(lamp)

    d = fr.design("demo_parts", place="C1")
    d.location("C1", "Cabinet")
    d.add(star, "U1")
    for n in range(parent_lamps):
        d.detail.wire(
            d.device(f"P{10 + n}", "DEMO-LAMP-24")["1"],
            d.device(f"P{50 + n}", "DEMO-LAMP-24")["1"],
            wire=("WH", 0.75),
        )
    with tempfile.TemporaryDirectory() as tmp:
        cover = Path(tmp) / "cover.md"
        cover.write_text("# Star\n", encoding="utf-8")
        preset = fr.DocumentPreset.CABINET_SCHEMATIC
        return fr.build(d, fr.document(preset, "demo-star", cover=cover)).model


def _unit_fit(parent_lamps: int):
    model = _star_model(parent_lamps=parent_lamps)
    kit = box_kit(model)
    (unit,) = {s.of_unit for s in drawing_scopes(model, kit) if s.of_unit is not None}
    return link_fit(model, kit, LIBRARY, unit), link_fit(model, kit, LIBRARY, None)


def test_a_unit_built_alone_has_the_link_fit_it_has_inside_its_parent() -> None:
    """The unit reads its own symbols and sheets only; the parent's lamps widen the parent's fit."""
    alone, _ = _unit_fit(0)
    inside, parent = _unit_fit(12)
    assert alone == inside
    assert parent["R0"].w > inside["R0"].w
