"""The contact tables and the built `Sym` values of a kit, as the symdef layer gives them."""

from typing import TYPE_CHECKING

from conventions_fixtures import house
from fransys_el.placement_env import make_env
from fransys_el.placement_syms import syms_of

from electrical_symbols import LIBRARY

if TYPE_CHECKING:
    from fransys_el.placement_kit import SymbolKit

    from fransys_layout.core import Box, Sym
    from fransys_model.kernel import Model

__all__ = ["syms", "tables"]


def tables(model: Model, kit: SymbolKit) -> dict[str, Box]:
    """The contact-table box of each coil of `kit` that has one, by symbol id."""
    found: dict[str, Box] = {}
    syms_of(make_env(model, kit, house(), LIBRARY), found)
    return found


def syms(model: Model, kit: SymbolKit) -> list[Sym]:
    """The layer-built `Sym` of each function of `kit`."""
    return list(syms_of(make_env(model, kit, house(), LIBRARY)))
