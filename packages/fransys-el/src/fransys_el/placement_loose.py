"""Symbols on no net and under no anchor: el leaves them off the page and says so (R336, R364)."""

from typing import TYPE_CHECKING

from fransys_model.derive import function_item
from fransys_model.kernel import render_id

from .kit_keys import function_of
from .placement_skips import FUNCTION_UNWIRED, SPARE_FUNCTION, Skipped, in_order

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fransys_layout.core import Anchor, Net, Sym

    from .placement_env import Env

__all__ = ["without_loose"]


def without_loose(
    env: Env, syms: Sequence[Sym], nets: Sequence[Net], anchors: Sequence[Anchor]
) -> tuple[tuple[Sym, ...], tuple[Skipped, ...]]:
    """The symbols a net or anchor touches, and a `Skipped` per function whose symbol none does.

    A function on an item that keeps another function is a spare (SPARE_FUNCTION); one whose
    item keeps none is not wired (FUNCTION_UNWIRED).
    """
    touched = {ref.sym for net in nets for ref in net.pins} | {a.pin.sym for a in anchors}
    kept = tuple(s for s in syms if s.id in touched)
    gone = {s.id for s in syms} - touched
    item = {f: function_item(env.model, function_of(env.model, f)) for f in env.owner}
    live = {item[f] for f, sid in env.owner.items() if sid in touched}
    lost = {
        Skipped("function", render_id(f), SPARE_FUNCTION if item[f] in live else FUNCTION_UNWIRED)
        for f, sid in env.owner.items()
        if sid in gone
    }
    return kept, in_order(lost)
