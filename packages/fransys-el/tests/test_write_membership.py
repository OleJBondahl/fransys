"""`write_layout` writes one `Membership` per function, port, conductor end and item per page (F7).

The planted model of `test_write` solves once; rows are read back from the written model.
"""

from dataclasses import replace

import pytest
from conventions_fixtures import house
from fransys_el import build, options, write_layout
from fransys_el.kit_keys import function_of
from fransys_el.placement_ids import symbol_ids
from placement_fixtures import kit_for, planted_model

from electrical_symbols import LIBRARY
from fransys_layout.core import solve
from fransys_model.derive import frame_cell as cell
from fransys_model.kernel import Origin, evolve, make_id
from fransys_model.layout import Membership, Page, Shown, layout_of


class Written:
    """The planted model, its solved layout and the written model."""

    def __init__(self) -> None:
        self.model = planted_model()
        self.kit = kit_for(self.model)
        conventions = house()
        problem, _ = build(self.model, self.kit, conventions, LIBRARY)
        self.layout = solve(problem, options(conventions, LIBRARY))
        self.out, _ = write_layout(
            self.model,
            None,
            self.layout,
            problem,
            self.kit,
            library=LIBRARY,
        )
        self.rows = list(layout_of(self.out, Membership).values())


@pytest.fixture(scope="module")
def written() -> Written:
    return Written()


def _fields(rows: list[Membership]) -> set[str]:
    names = ("function", "port", "conductor", "item")
    return {n for r in rows for n in names if getattr(r, n) is not None}


def test_every_subject_kind_has_rows(written: Written) -> None:
    assert _fields(written.rows) == {"function", "port", "conductor", "item"}
    assert all(r.page is not None and r.sheet is None for r in written.rows)


def _placed_functions(w: Written) -> dict[object, tuple[int, int, int]]:
    """Each placed lead function with its (page, y, x)."""
    ids = symbol_ids(w.model, w.kit)
    at = {p.sym: (p.page, p.y, p.x) for pg in w.layout.placement.pages for p in pg.placed}
    return {function_of(w.model, k): at[ids[k]] for k in w.kit if ids[k] in at}


def test_each_placed_function_has_a_row(written: Written) -> None:
    assert _placed_functions(written).keys() <= {r.function for r in written.rows}


def test_shown_is_set_on_port_and_conductor_rows_only(written: Written) -> None:
    for row in written.rows:
        applies = row.port is not None or row.conductor is not None
        assert (row.shown is not None) == applies
    ports = [r for r in written.rows if r.port is not None]
    assert {r.shown for r in ports} <= {Shown.DRAWN, Shown.REFERENCE}
    assert any(r.shown is Shown.DRAWN for r in ports)
    assert any(r.shown is Shown.REFERENCE for r in ports)


def test_rank_reads_top_down_left_to_right_on_each_page(written: Written) -> None:
    for page in layout_of(written.out, Page).values():
        ranks = [r.rank for r in written.rows if r.page == page.id]
        assert sorted(ranks) == list(range(len(ranks)))
    where = _placed_functions(written)
    by_page = {}
    for r in written.rows:
        if r.function in where:
            by_page.setdefault(r.page, []).append((r.rank, where[r.function]))
    for rows in by_page.values():
        places = [(y, x) for _, (_, y, x) in sorted(rows, key=lambda one: one[0])]
        assert places == sorted(places)


def test_the_cell_is_the_frame_position_of_the_place(written: Written) -> None:
    pages = layout_of(written.out, Page)
    where = _placed_functions(written)
    for r in written.rows:
        if r.function in where:
            number, y, x = where[r.function]
            page = next(p for p in pages.values() if p.id == r.page)
            assert page.number == number
            assert (r.cell.column, r.cell.row) == cell(written.out, page, x, y)


def test_keys_and_ids_are_deterministic(written: Written) -> None:
    again = Written()
    assert [r.key for r in again.rows] == [r.key for r in written.rows]
    assert len({r.key for r in written.rows}) == len(written.rows)


def test_a_rerun_replaces_only_its_own_membership_rows(written: Written) -> None:
    """R166, R196(a): a re-run keeps a foreign writer's row and rewrites our own."""
    mine = written.rows[0]
    foreign = replace(
        mine,
        id=make_id(Membership, ("other", "writer")),
        key=("other", "writer"),
        produced_by="other/writer",
    )
    stale = replace(mine, id=make_id(Membership, ("stale",)), key=(*mine.key[:4], "stale"))
    base = evolve(
        written.out,
        put=(foreign, stale),
        origin=Origin(file="test_write_membership.py", line=1, note="foreign row"),
    )
    conventions = house()
    problem, _ = build(written.model, written.kit, conventions, LIBRARY)
    layout = solve(problem, options(conventions, LIBRARY))
    again, _ = write_layout(base, None, layout, problem, written.kit, library=LIBRARY)
    rows = layout_of(again, Membership)
    assert rows[foreign.id] == foreign
    assert stale.id not in rows
    assert {r.id for r in rows.values() if r.produced_by != "other/writer"} == {
        r.id for r in written.rows
    }
