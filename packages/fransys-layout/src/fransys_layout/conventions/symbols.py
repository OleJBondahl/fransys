"""The default symbol of a function: one first-match table over named function facts (T2).

Used when a model authors no `layout.symbol_choice` (decision layout-0105). Hit policy: first
match, in row order. The state rows (T2.1 to T2.10) come before the kind rows (T2.11 to T2.21),
and within the kind rows a gender row comes before the plain kind row, so a typed protection
draws by its type and an untyped or unknown one falls to the circuit breaker. `then` is the
symbol name. A function with no matching row draws a labelled box.
"""

from .rows import Row, Table, all_

_SWITCH = ("function_kind", "switch")
_GENERIC = ("function_kind", "generic")
_PROTECTION = ("function_kind", "protection")
_CONNECTOR = ("function_kind", "connector")


def _by_type(row: str, value: str, symbol: str) -> Row:
    return Row(row, all_(_PROTECTION, ("protection_type", value)), symbol)


def _kind(row: str, kind: str, symbol: str) -> Row:
    return Row(row, ("function_kind", kind), symbol)


SYMBOL_DEFAULTS = Table(
    "symbol defaults",
    "first match",
    (
        Row("T2.1", all_(_SWITCH, ("rest_state", "operated")), "make-contact"),
        Row("T2.2", all_(_SWITCH, ("rest_state", "rest")), "break-contact"),
        Row("T2.3", all_(_GENERIC, ("rest_state", "operated")), "make-contact"),
        Row("T2.4", all_(_GENERIC, ("rest_state", "rest")), "break-contact"),
        _by_type("T2.5", "none", "circuit-breaker"),
        _by_type("T2.6", "fuse", "fuse"),
        _by_type("T2.7", "mcb", "circuit-breaker"),
        _by_type("T2.8", "motor_breaker", "circuit-breaker"),
        _by_type("T2.9", "overload", "thermal-overload"),
        _by_type("T2.10", "rcd", "rcd"),
        _kind("T2.11", "coil", "operating-device"),
        Row("T2.12", all_(_CONNECTOR, ("connector_gender", "female")), "contact-female"),
        Row("T2.13", all_(_CONNECTOR, ("connector_gender", "male")), "contact-male"),
        _kind("T2.14", "connector", "contact"),
        _kind("T2.15", "contact_co", "change-over-contact"),
        _kind("T2.16", "contact_nc", "break-contact"),
        _kind("T2.17", "contact_no", "make-contact"),
        _kind("T2.18", "protection", "circuit-breaker"),
        _kind("T2.19", "plc_channel", "plc-channel"),  # C6: our own end symbol
        _kind("T2.20", "switch", "make-contact"),  # R7 B1: switch-disconnector stand-in
        _kind("T2.21", "terminal", "terminal"),
    ),
)
