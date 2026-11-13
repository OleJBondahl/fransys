"""`link_fit`: the arrow's box is sized for the widest line the pages can print (R350)."""

import tempfile
from pathlib import Path
from typing import NamedTuple, cast

import fransys as fr
import pytest
from conventions_fixtures import house
from fransys_el import build, lay_out_drawn, symbol_kit
from fransys_el.placement_ids import symbol_ids
from fransys_el.placement_markers import LONE
from fransys_el.placement_sets import drawing_scopes
from fransys_el.placement_views import marker_boxes
from fransys_el.placement_widest import link_fit
from fransys_el.read_markers import drawn_marker
from kit_instances import INSTANCES
from ring_cases import box_kit, channels_model

from electrical_symbols import LIBRARY, MARKER_FACING, MARKER_TURN_FACING, MARKER_TURNED, marker_symbol
from fransys_layout.symbols import library_symbol, marker_rule
from fransys_model.derive.drawing_text import marker_text
from fransys_model.layout import LinkMarker, layout_of
from fransys_model.vocab.tables import documents
lazy from fransys_layout.core import Orientation


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


def _star_model(*, parent_lamps: int, own_document: bool = True):
    """A three-lamp unit, alone or inside a parent that draws `parent_lamps` lamps of its own."""

    class _Io(NamedTuple):
        lamp: object

    @fr.unit("demo-star", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
    def star(u: fr.Design) -> _Io:
        lamp, second, third = (u.device(f"P{n}", "DEMO-LAMP-24") for n in (2, 3, 4))
        u.series(lamp["1"], second["1"], wire=("WH", 0.75))
        u.series(lamp["1"], third["1"], wire=("WH", 0.75))
        u.series(lamp["2"], second["2"], wire=("WH", 0.75))
        u.series(lamp["2"], third["2"], wire=("WH", 0.75))
        return _Io(lamp)

    d = fr.design("demo_parts", place="C1")
    cabinet = d.location("C1", "Cabinet")
    if own_document:
        d.add(star, "U1")
    for n in range(parent_lamps):
        first, second = d.device(f"P{10 + n}", "DEMO-LAMP-24"), d.device(f"P{50 + n}", "DEMO-LAMP-24")
        d.series(first["1"], second["1"], wire=("WH", 0.75))
        d.series(first["2"], second["2"], wire=("WH", 0.75))
    with tempfile.TemporaryDirectory() as tmp:
        cover = Path(tmp) / "cover.md"
        cover.write_text("# Star\n", encoding="utf-8")
        preset = fr.DocumentPreset.CABINET_SCHEMATIC
        own = [fr.document(preset, "demo-star", cover=cover)] if own_document else []
        return fr.build(d, *own, fr.document(preset, cabinet, cover=cover)).model


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


@pytest.mark.rule("REF-BOX-OWN-LENGTH")
def test_a_tag_box_of_a_multi_document_build_is_the_single_document_one() -> None:
    """Every end of a reference stands in one set that one document prints, so no tag prints a scope (R2066): a second document adds no width."""
    many, one = _star_model(parent_lamps=1), _star_model(parent_lamps=1, own_document=False)
    assert len(documents(many)) == 2
    assert len(documents(one)) == 1
    assert link_fit(many, box_kit(many), LIBRARY, None) == link_fit(one, box_kit(one), LIBRARY, None)


def _laid_markers(model, kit):
    conventions = house()
    problem, _ = build(model, kit, conventions, LIBRARY)
    laid, *_ = lay_out_drawn(model, kit, problem, conventions, LIBRARY)
    return laid, list(layout_of(laid, LinkMarker).values())


def _body(rec, size):
    """The body box a marker of `rec`'s facing draws at `size`, and its orientation."""
    side = rec.facing.name
    along = side in MARKER_TURN_FACING
    orient = cast("Orientation", (MARKER_TURN_FACING if along else MARKER_FACING)[side])
    key = MARKER_TURNED if along else marker_symbol(rec.key[3])
    return marker_rule(library_symbol(LIBRARY, key), orient, size, LIBRARY, along=along)[1], orient


@pytest.mark.rule("REF-BOX-OWN-LENGTH")
def test_a_drawn_tag_is_the_box_of_its_own_text_inside_the_reserve_and_a_stub_keeps_its_record() -> None:
    """R2175: tags of different texts draw different lengths, each the measured box of its text and inside the `link_fit` reserve."""
    model = channels_model(23)
    laid, records = _laid_markers(model, box_kit(model))
    tags = [r for r in records if r.key[3] not in LONE]
    assert tags
    lengths = set()
    for rec in tags:
        out = drawn_marker(laid, rec, LIBRARY).outline
        assert out is not None
        reserve, _ = _body(rec, (rec.width, rec.height))
        own = marker_boxes(LIBRARY, marker_text(laid, rec))[cast("Orientation", MARKER_FACING[rec.facing.name])]
        want, _ = _body(rec, (own.w, own.h))
        assert (out.w, out.h) == (want.w, want.h)
        assert out.w <= reserve.w
        assert out.h <= reserve.h
        lengths.add(out.w + out.h)
    assert len(lengths) > 1
    model = INSTANCES["w07"]()
    laid, records = _laid_markers(model, symbol_kit(model, LIBRARY))
    stubs = [r for r in records if r.key[3] in LONE]
    assert stubs
    for rec in stubs:
        out = drawn_marker(laid, rec, LIBRARY).outline
        assert out is not None
        want, _ = _body(rec, (rec.width, rec.height))
        assert (out.w, out.h) == (want.w, want.h)
