"""One reference end in two drawing sets is two link markers, never one id twice (TEXT-CANDIDATES).

A net whose ends stand on page 1 of two sets gave the same `layout.link_marker` key from both
sets' write, with a different page: `MergeConflict` out of build. The set's number is in the key.
"""

import pytest
from conventions_fixtures import house
from fransys_el import build, options, symbol_kit
from fransys_el.write_markers import link_markers
from kit_instances import INSTANCES

from electrical_symbols import LIBRARY
from fransys_layout.core import solve
from fransys_model.kernel import make_id
from fransys_model.layout import DrawingSet, Page, PageRole


def _page(number: int, n: int) -> Page:
    key = ("test", str(number), str(n))
    return Page(
        id=make_id(Page, key), key=key, drawing_set=make_id(DrawingSet, key[:2]),
        number=n, role=PageRole.POWER,
        sheet_format=None, groups=(), produced_by="t",
    )  # fmt: skip


@pytest.fixture(scope="module")
def sets():
    """The markers of one layout written as set 1 and as set 2, whose pages have other ids."""
    model = INSTANCES["p02"]()
    kit = symbol_kit(model, LIBRARY)
    conventions = house()
    problem, _ = build(model, kit, conventions, LIBRARY)
    layout = solve(problem, options(conventions, LIBRARY))
    nos = {m.page for m in layout.annotations.markers}
    found = []
    for number in (1, 2):
        pages = {n: _page(number, n) for n in nos}
        found.append(
            link_markers(
                layout, model, kit, pages, stamp="t", library=LIBRARY, number=number, unit=None
            )
        )
    return model, found


def test_a_marker_of_two_sets_has_two_keys(sets) -> None:
    _, (first, second) = sets
    assert len(first) > 0
    assert not {m.key for m in first} & {m.key for m in second}
    assert not {m.id for m in first} & {m.id for m in second}
