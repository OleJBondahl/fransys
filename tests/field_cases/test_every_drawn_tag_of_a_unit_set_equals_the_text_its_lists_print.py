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

from fransys_model.layout import DrawingSet, Page, layout_of
from fransys_model.vocab.tables import items, ports

run: Any = None if is_export() else importlib.import_module("placement_corpus.run")

_CORPUS = {"machine_panel", "panel_di16p", "remote_io", "distribution_board", "mcc"}
_CASES = (
    [("export",)]  # one placeholder, skipped by its marker (R462)
    if run is None
    else [c for c in run.circuits("standard") if c[0] in _CORPUS] + [("demo-skid", run.load(run.SKID, "demo_skid"), {}, {})]
)


def _forms(model: Any, unit: Any) -> set[str]:
    found = {fr.derive.printed_designation(model, i, unit=unit) for i in items(model)}
    return found | {fr.derive.port_designation(model, p, unit=unit) for p in ports(model)}


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
