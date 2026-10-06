"""The default symbol of a switch, generic or protection function (decision layout-0105, T2).

The rows that read a rest state or a protection type of `SYMBOL_DEFAULTS` are the hook
`resolve` calls first; the rows of kind, category and gender reach it as `DEFAULT_RULES`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fransys_layout.conventions import FACTS, Table, first_match, validate
from fransys_layout.conventions.symbols import SYMBOL_DEFAULTS
from fransys_layout.stages import resolve

from .defaults import STAGE_FACTS, row_pairs
from .read.symbol_facts import SymbolSubject

if TYPE_CHECKING:
    from fransys_layout.stages import DrawnFunction, FunctionSpec, SymbolChoice, SymbolRule
    from fransys_model.kernel import Finding

validate(SYMBOL_DEFAULTS, FACTS)

# The state rows: every row `stage_rules` leaves out, in table order.
STATE_ROWS = Table(
    SYMBOL_DEFAULTS.name,
    SYMBOL_DEFAULTS.policy,
    tuple(r for r in SYMBOL_DEFAULTS.rows if not row_pairs(r).keys() <= STAGE_FACTS),
)


def default_symbol(kind: str, rest: str | None, protection_type: str | None) -> str | None:
    """The symbol `kind` draws by its state rows, or None; `rest` is `link_state`'s answer."""
    row = first_match(STATE_ROWS, SymbolSubject(kind, rest, protection_type, None, None), FACTS)
    return None if row is None else str(row.then)


def resolve_with_defaults(
    functions: tuple[FunctionSpec, ...],
    rules: tuple[SymbolRule, ...],
    choices: tuple[SymbolChoice, ...],
) -> tuple[tuple[DrawnFunction, ...], tuple[Finding, ...]]:
    """`stages.resolve` with the state rows as its default-symbol step (decision layout-0105 T5)."""
    return resolve(functions, rules=rules, choices=choices, default_symbol=default_symbol)
