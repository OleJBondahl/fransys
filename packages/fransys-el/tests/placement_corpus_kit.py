"""The symbol kit of a corpus model, chosen by the rule today's layout uses (P1-6).

`corpus_kit` runs the legacy path up to its resolve stage, without file I/O: `read_inputs`
(the choices and function facts), `without_loose` (a function with nothing connected is not
drawn) and `resolve_with_defaults` (symbol rules, state rows). Each resolved function gives
one `Pick`: key = the symbol key (`geometry.key`), poles = `geometry.poles`, ports = each
bound model port (`DrawnPort.port`) to its symbol port name (`DrawnPort.symbol_port`).
`members` stays empty: the legacy path draws every function with its own symbol.
Copies (`name@k` ids) are not in `functions`, so a function has one pick.
"""

from typing import TYPE_CHECKING

from fransys_el import OPTIONS, Pick, SymbolKit

from fransys_layout.engines.schematic.defaults import DEFAULT_RULES
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.engines.schematic.read.loose import without_loose
from fransys_layout.engines.schematic.symbol_defaults import resolve_with_defaults

if TYPE_CHECKING:
    from fransys_model.kernel import Model

__all__ = ["corpus_kit"]


def corpus_kit(model: Model) -> SymbolKit:
    """The kit of `model`: the symbol today's resolve stage draws each drawn function with."""
    inputs = without_loose(model, read_inputs(model, options=OPTIONS))
    drawn, _ = resolve_with_defaults(inputs.functions, DEFAULT_RULES, inputs.choices)
    return frozendict(
        {
            d.function: Pick(
                d.geometry.key,
                d.geometry.poles,
                frozendict({p.port: p.symbol_port for p in d.ports}),
            )
            for d in drawn
        }
    )
