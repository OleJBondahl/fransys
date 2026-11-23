"""Module-scoped placement fixtures shared by the placement test files."""

import pytest
from conventions_fixtures import house
from fransys_el import build, symbol_kit
from fransys_el.placement_env import Env, make_env
from fransys_el.placement_syms import syms_of
from placement_fixtures import demo_model, kit_for, planted_model

from electrical_symbols import LIBRARY
lazy from fransys_layout.core import PlacementProblem, Sym
lazy from fransys_model.kernel import Model


@pytest.fixture(scope="module")
def planted() -> tuple[Env, tuple[Sym, ...]]:
    """The planted model's env and syms, built once for the module."""
    model = planted_model()
    env = make_env(model, kit_for(model), house(), LIBRARY)
    return env, syms_of(env)


@pytest.fixture(scope="module")
def demo() -> tuple[Env, tuple[Sym, ...]]:
    """The demo model's env and syms, built once for the module."""
    model = demo_model()
    env = make_env(model, kit_for(model), house(), LIBRARY)
    return env, syms_of(env)


@pytest.fixture(scope="module")
def problem(model: Model) -> PlacementProblem:
    """The placement problem of the module's `model` fixture."""
    built, _ = build(model, symbol_kit(model, LIBRARY), house(), LIBRARY)
    return built
