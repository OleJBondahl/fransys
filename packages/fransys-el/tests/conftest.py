"""Module-scoped placement fixtures shared by the placement test files."""

import pytest
from conventions_fixtures import house
from fransys_el.placement_env import Env, make_env
from fransys_el.placement_syms import syms_of
from placement_fixtures import demo_model, kit_for, planted_model

from electrical_symbols import LIBRARY
lazy from fransys_layout.core import Sym


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
