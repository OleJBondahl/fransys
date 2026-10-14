"""The default symbol of a function: one first-match table over named function facts.

Used when a model authors no `layout.symbol_choice` (decision layout-0105). Hit policy: first
match, in row order. The operator rows (layout-0220) come first, then the state rows, then
the kind rows, and within the kind rows a gender row comes before the plain kind row, so a
typed protection draws by its type and an untyped or unknown one falls to the circuit
breaker. `then` is the symbol name. A function with no matching row draws a labelled box.
"""

from .rows import Row, Table, all_

_SWITCH = ("function_kind", "switch")
_GENERIC = ("function_kind", "generic")
_PROTECTION = ("function_kind", "protection")
_CONNECTOR = ("function_kind", "connector")
_APART = ("actuator_drawn", "no")


def _by_type(row: str, value: str, symbol: str) -> Row:
    return Row(row, all_(_PROTECTION, ("protection_type", value)), symbol)


def _operated(row: str, operator: str, rest: str, symbol: str) -> Row:
    # layout-0220: a switch by what operates it and its rest state
    return Row(row, all_(_SWITCH, ("operated_by", operator), ("rest_state", rest)), symbol)


def _kind(row: str, kind: str, symbol: str) -> Row:
    return Row(row, ("function_kind", kind), symbol)


# A row's `port_map`, model port name to symbol port: only the terminal row has one, the
# `external` side of a terminal with no part. The author's part-less terminal and the demo terminal
# part name that port `external`, so the name lives in two packages.
SYMBOL_PORT_MAPS: frozendict[str, frozendict[str, str]] = frozendict(
    {"T2.21": frozendict({"external": "s"})}
)

SYMBOL_DEFAULTS = Table(
    "symbol defaults",
    "first match",
    (
        # layout-0237: a grouped switch other than its lead draws its contact alone, with the
        # marks that belong to the contact (an e-stop's positive opening)
        Row(
            "T2.29",
            all_(_SWITCH, _APART, ("operated_by", "mushroom"), ("rest_state", "rest")),
            "break-contact-positive-opening",
        ),
        Row("T2.30", all_(_SWITCH, _APART, ("rest_state", "operated")), "make-contact"),
        Row("T2.31", all_(_SWITCH, _APART, ("rest_state", "rest")), "break-contact"),
        _operated("T2.22", "push", "operated", "push-button"),
        _operated("T2.23", "push", "rest", "push-button-break"),
        _operated("T2.24", "mushroom", "rest", "emergency-stop"),
        _operated("T2.25", "turn", "operated", "selector-make"),
        _operated("T2.26", "turn", "rest", "selector-break"),
        _operated("T2.27", "position", "operated", "position-switch-make"),
        _operated("T2.28", "position", "rest", "position-switch-break"),
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
        _kind("T2.19", "plc_channel", "plc-channel"),  # Our own end symbol
        _kind("T2.20", "switch", "make-contact"),  # Switch-disconnector stand-in
        _kind("T2.21", "terminal", "terminal"),
    ),
)
