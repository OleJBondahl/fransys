"""The input-card instances of the study, rebuilt from the tests their dumps name (Ruling 43.2).

Each model comes from the builder of the field-case test the dump's first line names, loaded by
path, and goes through `fransys_el.build` and `solve`. `w09` is the second build of its test (the
fan, `__2`); the first (interleaved) is an extra.
"""

import importlib.util
import sys
from dataclasses import replace
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

import fransys as fr
from conventions_fixtures import house
from fransys_el import build, options, symbol_kit

from electrical_symbols import LIBRARY
from fransys_layout.core import solve

if TYPE_CHECKING:
    from collections.abc import Callable

    from fransys_layout.core import CoreLayout, Options, PlacementProblem
    from fransys_model.kernel import Model

__all__ = ["DESIGNS", "built", "counts", "solve_problem", "solved"]

ROOT = Path(__file__).resolve().parents[3]
W01 = "test_a_series_to_a_plc_module_takes_its_lowest_free_channel"
W09 = "test_an_input_card_prints_its_pins_in_marking_order_whatever_its_partners_order"
W03 = "test_plc_list_pin_of_a_later_channel"
P02 = "test_a_strip_wired_outside_routes_every_wire_to_a_plc_module_under_it"


def _case(name: str) -> Any:
    """A field-case module, loaded by path (it imports its helpers from `tests/`)."""
    sys.path.insert(0, str(ROOT / "tests"))
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "tests" / "field_cases" / f"{name}.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def w01() -> Model:
    """Sixteen series buttons to one module: the test's `_design` and `_button`."""
    case = _case(W01)
    d, dc, module = case._design()
    for number in range(1, case.COUNT + 1):
        case._button(d, dc, module, number)
    return fr.build(d).model


def w09() -> Model:
    """The fan: six contacts, each fed from its own connector pin and wired to a channel."""
    return _case(W09)._built("fan")


def w09_interleaved() -> Model:
    """Extra: three groups of two contactors whose channels interleave (the test's first build)."""
    return _case(W09)._built("interleaved")


def w03() -> Model:
    """A 4-channel analog card, each channel wired to a connector header: the fixture's body."""
    return _case(W03).built.__wrapped__().model


def p02() -> Model:
    """A unit strip wired to a module inside the unit and on to a field strip."""
    return _case(P02)._built().model


DESIGNS: dict[str, Callable[[], Model]] = {
    "w01": w01,
    "w09": w09,
    "w09_interleaved": w09_interleaved,
    "w03": w03,
    "p02": p02,
}


@cache
def built(name: str) -> tuple[Model, PlacementProblem]:
    """The model of the design `name` and its placement problem (the kit's pick, el-0011)."""
    model = DESIGNS[name]()
    problem, _ = build(model, symbol_kit(model, LIBRARY), house(), LIBRARY)
    return model, problem


def solve_problem(problem: PlacementProblem, **plant: Any) -> CoreLayout:
    """`problem` on the core; `plant` replaces fields of the house options."""
    chosen: Options = options(house(), LIBRARY)
    return solve(problem, replace(chosen, **plant))


def solved(name: str, **plant: Any) -> CoreLayout:
    """The design `name` on the core; `plant` replaces fields of the house options."""
    return solve_problem(built(name)[1], **plant)


def counts(layout: CoreLayout) -> dict[str, int]:
    """The scorer's counts of a layout: crossings `X` and each placement term by name."""
    score = layout.score
    assert score is not None
    return {"X": score.X, **dict(score.P)}
