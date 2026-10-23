"""P7.3 (SW8, el-0008): the strip instances solved on the core with the generic builder.

w04 is rebuilt from its named field test (Ruling 43.2); the own 4-terminal case is an extra.
Each builds and solves once for the module, with no facade and no markers: the counts are the
core's `Score`, `references` and `findings`.
"""

import importlib.util
import sys
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Any

import fransys as fr
import pytest
from conventions_fixtures import house, tables_on
from fransys_el import build, options, symbol_kit

from electrical_symbols import LIBRARY
from fransys_layout.core import Size, solve
from fransys_model.derive import function_item, strip_of
from fransys_model.vocab import ports

if TYPE_CHECKING:
    from fransys_layout.core import CoreLayout, PlacementProblem
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Item

W04 = "test_a_terminal_wired_to_devices_on_two_pages_is_drawn_on_each"
P02 = "test_a_strip_wired_outside_routes_every_wire_to_a_plc_module_under_it"
OWN = "test_a_strip_feeding_a_relay_bank_draws_with_no_strip_reference"
ROOT = Path(__file__).resolve().parents[3]


def _case_module(name: str) -> Any:
    """A field-case module, loaded by path (`--import-mode=importlib` keeps it off `sys.path`)."""
    sys.path.insert(0, str(ROOT / "tests"))
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "tests" / "field_cases" / f"{name}.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _own_model() -> Model:
    with tempfile.TemporaryDirectory() as tmp:
        return fr.build(*_case_module(OWN).strip_case_drafts(Path(tmp) / "cover.md")).model


class Solved:
    """A model, its problem and its core layout."""

    def __init__(self, model: Model, width: int | None = None, *, tables: bool = False) -> None:
        self.model = model
        self.conventions = tables_on() if tables else house()
        if width is not None:
            area = Size(width, self.conventions.area.h)
            self.conventions = replace(self.conventions, area=area)
        kit = symbol_kit(self.model, LIBRARY)
        self.problem: PlacementProblem
        self.problem, _ = build(self.model, kit, self.conventions, LIBRARY)
        self.layout: CoreLayout = solve(self.problem, options(self.conventions, LIBRARY))

    def strips(self) -> set[Id[Item]]:
        """The strip items of the model that have a terminal."""
        found = {
            strip_of(self.model, function_item(self.model, port.function))
            for port in ports(self.model).values()
        }
        return {strip for strip in found if strip is not None}

    def strip_references(self) -> int:
        """The references with an end on a symbol of a strip row."""
        in_row = {sym.id for sym in self.problem.symbols if sym.row_group}
        return sum(
            1
            for ref in self.layout.references
            if any(end.pin is not None and end.pin.sym in in_row for end in ref.ends)
        )

    def penalty(self, name: str) -> int:
        assert self.layout.score is not None
        return dict(self.layout.score.P)[name]


@pytest.fixture(scope="module")
def solved() -> Solved:
    return Solved(_own_model())


@pytest.fixture(scope="module")
def w04() -> Solved:
    """The study instance w04: its named test's builder (chained), through `fransys_el.build`."""
    return Solved(_case_module(W04)._model(chained=True), tables=True)


def test_the_case_has_the_strip_and_a_net_wired_to_it(solved: Solved) -> None:
    assert len(solved.strips()) == 1
    assert any(sym.row_group for sym in solved.problem.symbols)


def test_no_reference_stands_on_a_strip_terminal(solved: Solved) -> None:
    """The own case: today's engine draws 22 link markers on it; the core stands none on a strip."""
    layout = solved.layout
    assert layout.score is not None
    assert solved.strip_references() == 0, (
        f"strip references {solved.strip_references()}, all references {len(layout.references)},"
        f" Score.R {layout.score.R}"
    )


def test_the_strip_rows_are_whole(solved: Solved) -> None:
    assert solved.penalty("row_broken") == 0


def test_w04_no_reference_stands_on_a_strip_terminal_on_one_page(w04: Solved) -> None:
    """SW8 P7.3 and Ruling 43 on w04 (22 references and 2 pages today): strip references 0, 1 page.

    The like-for-like reference count is this one: the old 22 were all link markers on the strip.
    """
    assert w04.layout.score is not None
    assert w04.strip_references() == 0, f"strip references, Score.R {w04.layout.score.R}"
    assert w04.layout.score.pages == 1
    assert w04.penalty("row_broken") == 0


def test_w04_with_the_tables_on_the_only_findings_are_the_unplaced_tables(w04: Solved) -> None:
    """The tables left the footprint (R327), so the strip row group aligns: no ALIGN_DROPPED. With
    `contact_tables` on, the only findings are the tables nothing fits beside (the known gap).
    """
    codes = {f.code for f in w04.layout.findings}
    assert codes == {"ANNEX_UNPLACED"}


def test_w04_with_the_tables_off_has_no_finding() -> None:
    """The default draws no contact table, so the strip row group aligns and nothing is dropped."""
    assert Solved(_case_module(W04)._model(chained=True)).layout.findings == ()


def test_w04_a_page_too_narrow_puts_a_reference_on_a_strip_terminal() -> None:
    """Can fail on the real w04 build: at 340 G wide the counter finds the references it counts."""
    narrow = Solved(_case_module(W04)._model(chained=True), width=340)
    assert narrow.strip_references() >= 1, f"references {len(narrow.layout.references)}"


def test_p02_a_strip_to_a_plc_card_has_no_terminal_off_column() -> None:
    """The study instance p02, rebuilt from its named test: 13 terminals off column today (study).

    KIT-PINS gave the PLC card box its pick: p02 now builds, `junction_off_line` is 0, and 5
    references still stand on strip terminals (measured). SW8 P7.4 wants 0 (Ruling 43). Strict
    xfail: turn into a plain test, mark removed, when P7.4 lands.
    """
    p02 = Solved(_case_module(P02)._built().model)
    assert p02.strip_references() == 0
    assert p02.penalty("junction_off_line") == 0
