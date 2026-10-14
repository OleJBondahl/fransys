"""The stubs an open strip keeps (O5): what its terminals wire to outside the opened unit.

`strip_view` draws a terminal's lines to the level's boxes only; the connections that leave the
unit are the stubs of this module, one list per terminal. Reached as `derive.strip_stubs`.
"""

lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Item, Unit

from .memo import Memo
from .overview import links_of
from .overview_levels import level_box, merge_stubs, strip_view, stubs_of
from .rows_overview import TerminalStubs
lazy from .rows import OverviewStub

__all__ = ["strip_stubs"]


@Memo
def strip_stubs(model: Model, strip: Id[Item], unit: Id[Unit]) -> tuple[TerminalStubs, ...]:
    """The stubs of each terminal of `strip` opened on `unit`'s level, in strip order.

    A terminal wired to an item outside `unit` has one stub per far end, as the level's stubs are
    named (`stub_far_end`), standing at the terminal. A terminal with none has an empty tuple.
    """
    found = []
    for terminal in strip_view(model, strip, unit).terminals:
        stubs: list[OverviewStub] = []
        for link in links_of(model, terminal.item):
            other = link.b if link.a == terminal.item else link.a
            if level_box(model, other, unit) is None:
                stubs.extend(stubs_of(model, unit, link, terminal.item, other))
        found.append(TerminalStubs(terminal=terminal.item, stubs=merge_stubs(model, unit, stubs)))
    return tuple(found)
