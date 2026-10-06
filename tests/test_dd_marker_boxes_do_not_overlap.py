"""Layout cleanup step 5 (P0 iii): no two reference marker boxes overlap on a page.

The engineering shape: a contactor with a coil, a three-pole main contact and a wired NO
auxiliary contact (demo cabinet, `test_spare_contact_in_contact_table._plant`), every pole
wired to the supply, so the references stand side by side over the contactor's top poles.
The bug: on the cabinet's PDF page 2 the boxes over poles 5 and 13 overprint each other; a
box is one fixed width per drawing set (S4) and a pole's pitch is shorter than that width.
Decision layout-0114 fixes it. Read from the stage's markers: a marker with a `symbol` draws
a power symbol, and a non-lead marker shares its lead's box, so neither is a box of its own.
"""

import importlib.util
from collections import defaultdict
from itertools import combinations
from pathlib import Path

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.geometry import overlaps
from fransys_model.vocab.tables import ports


def _fixture():
    """`test_spare_contact_in_contact_table`, loaded by path (root tests are not a package)."""
    name = "test_spare_contact_in_contact_table"
    path = Path(__file__).with_name("field_cases") / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_no_two_marker_boxes_overlap_on_a_page() -> None:
    """Of the markers that draw a box of their own, none shares interior area with another."""
    model = _fixture()._built(hide=False).model
    results, _ = stage_results(model, read_inputs(model))
    pages = defaultdict(list)
    for one in results.layout.markers:
        if not one.symbol and one.lead:
            pages[one.drawing_set, one.page].append(one)
    assert pages
    name = {k: ".".join(v.key[-3:]) for k, v in ports(model).items()}
    clashes = [
        (page, name[a.port], a.box, name[b.port], b.box)
        for page, found in pages.items()
        for a, b in combinations(found, 2)
        if overlaps(a.box, b.box)
    ]
    assert not clashes, clashes
