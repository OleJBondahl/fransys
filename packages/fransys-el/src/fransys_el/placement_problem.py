"""`build`: the one function that turns a model into a `PlacementProblem` (el-0002)."""

from typing import TYPE_CHECKING

from fransys_layout.core import PlacementProblem

from .placement_env import make_env
from .placement_facts import facts_of
from .placement_hints import hints_of
from .placement_nets import nets_of
from .placement_skips import Skipped, in_order
from .placement_syms import syms_of

if TYPE_CHECKING:
    from fransys_model.kernel import Model

    from .placement_kit import SymbolKit
    from .placement_options import Conventions

__all__ = ["build"]


def build(
    model: Model, kit: SymbolKit, conventions: Conventions
) -> tuple[PlacementProblem, tuple[Skipped, ...]]:
    """The placement problem of `model` (symbols, nets, facts, hints) and what it left out.

    The `Skipped` omissions are a net with fewer than two drawn pins and a function with no symbol
    in a keep-whole set; P6.1 turns each into a finding. Raises `ProblemError` for a function the
    kit has no pick for, a hint naming a group nothing is drawn in, or a pin the kit does not name.
    """
    env = make_env(model, kit, conventions)
    syms = syms_of(env)
    nets, net_skips = nets_of(env, syms)
    facts, function_skips = facts_of(env, syms)
    problem = PlacementProblem(conventions.area, syms, nets, facts, hints_of(env, syms))
    return problem, in_order({*net_skips, *function_skips})
