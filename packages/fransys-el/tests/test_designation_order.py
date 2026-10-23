"""Equal columns stand in designation order, whatever order their Id hashes sort in (el-0006).

The core breaks ties by `natural_key` of the symbol id, so the id leads with the printed
designation. Twelve independent lamp pairs are equal columns: only the id orders them.
"""

import fransys as fr
from conventions_fixtures import house
from fransys.colours import BU
from fransys_el import build, options, symbol_kit
from fransys_el.placement_ids import symbol_key
from placement_fixtures import leads

from electrical_symbols import LIBRARY
from fransys_layout.core import natural_key, solve
from fransys_model.kernel import render_id
from fransys_model.vocab import functions, items

_PAIRS = 12


def _placed_tags() -> tuple[list, list]:
    """The tag of each lamp, left to right, top to bottom, and the tags in Id-text order."""
    d = fr.design("demo_parts")
    for i in range(1, _PAIRS + 1):
        first, second = d.device(f"P{i}", "DEMO-LAMP-24"), d.device(f"Q{i}", "DEMO-LAMP-24")
        d.detail.wire(first.lamp["2"], second.lamp["1"], wire=(BU, 0.5))
    model = fr.build(d).model
    kit = symbol_kit(model, LIBRARY)
    conventions = house()
    problem, _ = build(model, kit, conventions, LIBRARY)
    layout = solve(problem, options(conventions, LIBRARY))
    tag = {f.id: items(model)[f.item].tag for f in functions(model).values()}
    tag_of = {symbol_key(model, f): tag[f] for f in leads(kit)}
    placed = [p for page in layout.placement.pages for p in page.placed]
    by_id = sorted(leads(kit), key=lambda f: natural_key(render_id(f)))
    placed_tags = [tag_of[p.sym] for p in sorted(placed, key=lambda p: (p.page, p.y, p.x))]
    return placed_tags, [tag[f] for f in by_id]


def test_equal_columns_stand_in_designation_order() -> None:
    tags, id_order = _placed_tags()
    assert len(tags) == 2 * _PAIRS
    designation = sorted(tags, key=lambda t: (t[0] != "P", natural_key(t)))
    assert id_order != designation  # precondition: the Id text alone would order them otherwise
    assert tags == designation
