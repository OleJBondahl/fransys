"""Render draws in the library it is given: the build's font, grid and heights (SO-E, R494.1)."""

import dataclasses
from typing import Any, NamedTuple

import fransys as fr
import pytest
from fransys_render import bridge_pieces, cable_blocks, diagram_sheets, sheets

from electrical_symbols import LIBRARY
from fransys_layout import lay_out_cables
from fransys_model.derive import document_sheets_of

pytestmark = pytest.mark.wp("facade")

assert LIBRARY.font is not None
HOUSE_FAMILY = LIBRARY.font.family


class _Unit(NamedTuple):
    """A unit with no interface to hand back."""


@fr.unit("lib-value", revision=1, interface_version=1, date="2026-10-23", text="first", by="AB")
def _unit(c: Any) -> _Unit:
    x1 = c.terminal_strip("X1", "DEMO-TB-2.5", 4)
    h1 = c.device("H1", "DEMO-LAMP-24")
    c.cable("W2", "DEMO-CBL-2X2X0.75-SP", length_m=25).core(1, x1[2], h1[2])
    return _Unit()


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory):
    folder = tmp_path_factory.mktemp("lib-value")
    cover = folder / "cover.md"
    cover.write_text("# C\n", encoding="utf-8")
    d = fr.design("demo_parts")
    d.add(_unit, "U1")
    pages = (fr.PageKind.HARNESS_DRAWING, fr.PageKind.CABLE_LIST)
    preset = fr.DocumentPreset.CABINET_SCHEMATIC
    result = fr.build(d, fr.document(preset, "lib-value", cover=cover, add=pages))
    assert LIBRARY.font is not None
    font = dataclasses.replace(LIBRARY.font, family="Other Family")
    return result.model, dataclasses.replace(LIBRARY, font=font)


def test_cable_blocks_are_set_in_the_given_font(built) -> None:
    model, other = built
    laid = lay_out_cables(model)[0]
    house = "".join(cable_blocks(laid, LIBRARY).values())
    mine = "".join(cable_blocks(laid, other).values())
    assert HOUSE_FAMILY in house
    assert HOUSE_FAMILY not in mine
    assert "Other Family" in mine


def test_the_sheet_backgrounds_are_set_in_the_given_font(built) -> None:
    model, other = built
    listings = document_sheets_of(model)
    house = "".join(page.svg for page in sheets(listings, LIBRARY).values())
    mine = "".join(page.svg for page in sheets(listings, other).values())
    assert HOUSE_FAMILY in house
    assert HOUSE_FAMILY not in mine
    assert "Other Family" in mine


def test_a_diagram_without_sheets_and_the_bridge_pieces_take_the_library(built) -> None:
    model, other = built
    assert not diagram_sheets(model, other)
    assert set(bridge_pieces(other)) == set(bridge_pieces(LIBRARY))


def test_a_build_makes_its_library_once_for_the_build_and_every_write(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from fransys import pipeline

    calls: list[object] = []
    real = pipeline.library_of
    monkeypatch.setattr(pipeline, "library_of", lambda s: calls.append(s) or real(s))
    cover = tmp_path / "cover.md"
    cover.write_text("# C\n", encoding="utf-8")
    d = fr.design("demo_parts")
    d.add(_unit, "U1")
    preset = fr.DocumentPreset.CABINET_SCHEMATIC
    result = fr.build(d, fr.document(preset, "lib-value", cover=cover))
    assert result.library is not None
    fr.write(result, tmp_path / "out", intermediates=tmp_path / "tmp")
    fr.write(result, tmp_path / "out")
    fr.export_names(result)
    assert len(calls) == 1
