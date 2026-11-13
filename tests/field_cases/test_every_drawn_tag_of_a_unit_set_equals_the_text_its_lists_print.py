"""Field case: in every drawing set, a drawn tag equals the text the set's lists print for it.
The bug: the unit sets drew the root-relative form (`-U1-Q21`) beside lists that print `-Q21`.
Fixed by model-0359 (DESIGNATION-SCHEME), each TAG text of a set is the text printed_designation or port_designation gives."""

import importlib
from collections import defaultdict
from typing import Any

import fransys as fr
import pytest
from _drawn_pages import drawn_pages
from _export_signature import is_export

from fransys_model.derive import function_item, run_point_text, strip_of, strip_tag_text
from fransys_model.layout import DrawingSet, Page, layout_of
from fransys_model.vocab.tables import functions, items, ports

run: Any = None if is_export() else importlib.import_module("placement_corpus.run")

_CORPUS = {"machine_panel", "panel_di16p", "remote_io", "distribution_board", "mcc"}
_DRAW_RUNS = {"machine_panel", "panel_di16p", "distribution_board", "mcc", "demo-skid"}  # builds that draw a run (R2096)
_CASES = (
    [("export",)]  # one placeholder, skipped by its marker (R462)
    if run is None
    else [c for c in run.circuits("standard") if c[0] in _CORPUS] + [("demo-skid", run.load(run.SKID, "demo_skid"), {}, {})]
)


def _run_forms(model: Any, unit: Any) -> set[str]:
    """The forms a run prints (STRIP-TAG-ONCE): each strip terminal's own point and its strip's tag, in the set of `unit`."""
    strip_terminals = [f for f in functions(model) if strip_of(model, function_item(model, f))]
    return {run_point_text(model, f) for f in strip_terminals} | {strip_tag_text(model, f, unit=unit) for f in strip_terminals}


def _forms(model: Any, unit: Any) -> set[str]:
    found = {fr.derive.printed_designation(model, i, unit=unit) for i in items(model)}
    return found | {fr.derive.port_designation(model, p, unit=unit) for p in ports(model)} | _run_forms(model, unit)


def _tags_by_unit(model: Any) -> dict[Any, set[str]]:
    sets = layout_of(model, DrawingSet)
    page_set = {p.id: sets[p.drawing_set].unit for p in layout_of(model, Page).values()}
    found: dict[Any, set[str]] = defaultdict(set)
    for page, drawing in drawn_pages(model).items():
        found[page_set[page]] |= {t.text for t in drawing.texts if t.kind == "TAG"}
    return found


@pytest.mark.private_input  # reads internal/ (R462)
@pytest.mark.rule("DESIGNATION-SCHEME")
@pytest.mark.parametrize("case", _CASES, ids=[c[0] for c in _CASES])
def test_each_drawn_tag_of_a_set_is_a_text_its_lists_print(case: Any) -> None:
    model = run.build(case[0], case).model
    for unit, tags in _tags_by_unit(model).items():
        own = _forms(model, unit)
        assert tags <= own, (unit, sorted(tags - own)[:5])
        if unit is not None:
            root_only = _forms(model, None) - own
            assert not tags & root_only, (unit, sorted(tags & root_only)[:5])


@pytest.mark.private_input  # reads internal/ (R462)
@pytest.mark.rule("STRIP-TAG-ONCE")
@pytest.mark.parametrize("case", _CASES, ids=[c[0] for c in _CASES])
def test_a_page_that_prints_a_strip_points_prints_the_strip_tag(case: Any) -> None:
    """A page with a drawn run point (`L2:1`) also draws a strip tag of its set (`-X1`): no point stands without its run's tag."""
    model = run.build(case[0], case).model
    sets = layout_of(model, DrawingSet)
    pages = layout_of(model, Page)
    strip_terminals = [f for f in functions(model) if strip_of(model, function_item(model, f))]
    points = {run_point_text(model, f) for f in strip_terminals}
    printed_points: set[str] = set()
    for page, drawing in drawn_pages(model).items():
        unit = sets[pages[page].drawing_set].unit
        tags = {t.text for t in drawing.texts if t.kind == "TAG"}
        strips = {strip_tag_text(model, f, unit=unit) for f in strip_terminals}
        printed_points |= tags & points - strips
        if tags & points - strips:
            assert tags & strips, (page, sorted(tags)[:8])
    if case[0] in _DRAW_RUNS:
        assert printed_points, "no page prints a run point: the test would pass vacuously"
