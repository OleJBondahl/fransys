"""`fr.readability` counts the build's `BuildResult.drawings`, laying nothing out (R218, R255)."""

import dataclasses

import fransys as fr
from _motor_feeder_case import motor_feeder_case_drafts

from fransys_model.derive import set_unit, unit_release
from fransys_model.layout import DrawingSet, Page, layout_of
from fransys_model.vocab.tables import units


def _unit_of_each_page(result: fr.BuildResult) -> dict:
    sets = layout_of(result.model, DrawingSet)
    return {p.id: set_unit(sets[p.drawing_set]) for p in layout_of(result.model, Page).values()}


def test_readability_reads_the_build_drawings() -> None:
    result = fr.build(*motor_feeder_case_drafts())
    reading = fr.readability(result)
    assert tuple(row.page for row in reading.pages) == tuple(result.drawings)
    assert len(reading.pages) == len(result.drawings) > 0


def test_empty_drawings_give_zero_pages() -> None:
    """The error-build case (R249): no drawings, no rows, no refusal."""
    result = dataclasses.replace(fr.build(*motor_feeder_case_drafts()), drawings={})
    assert fr.readability(result).pages == ()


def test_each_page_names_the_unit_of_its_drawing_set() -> None:
    """A page belongs to one drawing set; its row names that set's unit, or none at the top."""
    result = fr.build(*motor_feeder_case_drafts())
    units = _unit_of_each_page(result)
    rows = fr.readability(result).pages
    assert rows
    assert all(row.unit == units[row.page] for row in rows)


def test_a_page_of_a_unit_reads_that_unit_not_none() -> None:
    """The facade passes the real unit map: a page in a unit's drawing set names the unit."""
    from test_dd_unit_one_drawing_set import _build

    result = _build(in_unit=True, nested=True)
    rows = fr.readability(result).pages
    assert rows
    (u1,) = (
        u.id for u in units(result.model).values() if unit_release(result.model, u.id).name == "u1"
    )
    assert {row.unit for row in rows} == {u1}
