"""Generic table-field checking shared by every part-file table.

One `_Field` spec per table (`_LIBRARY_FIELDS`, `_PART_FIELDS`, ...) says a field's raw TOML
type, whether it is required, and, for an enum field, which `fransys_model.vocab.enums`
class its value must name a member of. `check_fields` walks one against a parsed TOML table
and returns `FIELD_UNKNOWN`, `FIELD_MISSING`, `FIELD_TYPE` and `ENUM_VALUE` findings; it
never raises for a malformed table. `FLOAT_FORBIDDEN` is `_toml.value_findings`' job, not
this module's: a bare float must be reported wherever it sits, an unknown table or field
included, which a per-field walk over a fixed spec cannot see.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from fransys_model.elecdef import LinkKind, PinRole, Side, Unit
from fransys_model.vocab import (
    ConductorMark,
    Energy,
    FunctionKind,
    Gender,
    OperatedBy,
    PartCategory,
    PortBoundary,
    ProtectionType,
    SignalType,
    WiringRow,
)

from . import _toml

if TYPE_CHECKING:
    from enum import Enum

    from fransys_model.kernel import Finding


@dataclass(frozen=True, slots=True)
class _Field:
    """One field of a table spec: its raw TOML type, whether it is required, and its shape."""

    type_: type
    required: bool = True
    enum: type[Enum] | Mapping[str, object] | None = None
    elem_type: type | None = None


type Spec = dict[str, _Field]


@dataclass(frozen=True, slots=True)
class _Loc:
    """Where a table sits, threaded through the field checks that need to report it."""

    path: str
    line: int
    table_name: str


LIBRARY_FIELDS = {
    "schema": _Field(int),
    "name": _Field(str),
    "version": _Field(str),
    "description": _Field(str),
}
PART_FIELDS = {
    "mpn": _Field(str),
    "manufacturer": _Field(str),
    "description": _Field(str),
    "category": _Field(str, enum=PartCategory),
    "class_code": _Field(str),
    "operated_by": _Field(str, required=False, enum=OperatedBy),
}
FUNCTION_FIELDS = {
    "name": _Field(str),
    "kind": _Field(str, enum=FunctionKind),
    "symbol": _Field(str, required=False),
    "energy": _Field(str, required=False, enum=Energy),
    "ports": _Field(list),
    "links": _Field(list, required=False),
}

# The part file's `side` word (schema 2): `line` is elecdef Side.A, `load` Side.B; the model stores the Side
SIDE_WORDS = {"line": Side.A, "load": Side.B}

# The part file's `role` word: the boundary a pin is on and the pin role it states (schema 2)
ROLE_WORDS = {
    "generic": (PortBoundary.GENERIC, None),
    "internal": (PortBoundary.INTERNAL, None),
    "external": (PortBoundary.EXTERNAL, None),
    "pe": (PortBoundary.GENERIC, PinRole.PE),
    "common": (PortBoundary.GENERIC, PinRole.COMMON),
    "break": (PortBoundary.GENERIC, PinRole.BREAK),
    "make": (PortBoundary.GENERIC, PinRole.MAKE),
}


def port_roles(word: str, kind: str) -> tuple[PortBoundary, PinRole | None]:
    """The boundary and pin role of a pin whose `role` is `word`, on a function of `kind`: a coil pin is COIL."""
    boundary, pin_role = ROLE_WORDS[word]
    if word == "generic" and kind == FunctionKind.COIL.value:
        return boundary, PinRole.COIL
    return boundary, pin_role


PORT_FIELDS = {
    "name": _Field(str),
    "role": _Field(str, enum=ROLE_WORDS),
    "symbol_port": _Field(str, required=False),
    # The pin marking printed on the part; "" when it has none
    "marking": _Field(str, required=False),
    # parts-0010: stated pole side and IEC 60445 conductor; PE is a role, so "PE" is refused
    "side": _Field(str, required=False, enum=SIDE_WORDS),
    "conductor": _Field(str, required=False, enum=ConductorMark),
    # model-0260: the wiring row a pin sources (a drive output, a PSU secondary), by row name
    "source_row": _Field(str, required=False, enum=WiringRow),
    # parts-0017: a header pin's function port, "<function>.<port>" of the same part
    "joins": _Field(str, required=False),
}
# The part file spells a switched link's rest state as a word; the model stores `closed_at_rest`.
REST_WORDS = {"open": False, "closed": True}
LINK_FIELDS = {
    "a": _Field(str),
    "b": _Field(str),
    "kind": _Field(str, enum=LinkKind),
    "rest": _Field(str, required=False, enum=REST_WORDS),
}
SUPPLY_FIELDS = {
    "supplier": _Field(str),
    "supplier_part_number": _Field(str),
    "note": _Field(str, required=False),
}
FOOTPRINT_FIELDS = {"library": _Field(str), "name": _Field(str)}
CABLE_PRODUCT_FIELDS = {
    "core_count": _Field(int),
    "core_colours": _Field(list, elem_type=str),
    "gauge_mm2": _Field(str),
    "shielded": _Field(bool),
    # CC8: inline tables `{ cores = [1, 2], screen = 5 }`; their contents are the pair lint's
    "pairs": _Field(list, required=False, elem_type=dict),
}
CONNECTOR_FIELDS = {
    "style": _Field(str),
    "pincount": _Field(int),
    "gender": _Field(str, required=False, enum=Gender),  # model-0080: absent means not stated
    # parts-0003: the label printed on the part ("X1"); absent means the function's name
    "marking": _Field(str, required=False),
    # parts-0016: the MPNs this connector mates with, data only
    "mates": _Field(list, required=False, elem_type=str),
}


# `[function.block]` (schema 2): the protection `type`; its type decides the breaking figures it may state
BLOCK_FIELDS = {"type": _Field(str, required=False, enum=ProtectionType)}
BREAKER_KEYS = ("icn", "icu", "ics")
_BREAKING = {
    "fuse": {"breaking_capacity": _Field(list, required=False, elem_type=dict)},
    "mcb": {key: _Field(dict, required=False) for key in BREAKER_KEYS},
    "motor_breaker": {key: _Field(dict, required=False) for key in BREAKER_KEYS},
}
PLC_CHANNEL_FIELDS = {"signal": _Field(str, enum=SignalType), "channel": _Field(int)}
PCB_FIELDS = {"revision": _Field(str)}
# R1268: `[connection]` states the elecdef `Connection` of a terminal part's one function
CONNECTION_FIELDS = {"conductors_per_clamp": _Field(int)}
# parts-0004: `[rating]` holds elecdef figures
RATING_FIELDS = {
    "voltage": _Field(list, required=False, elem_type=dict),
    "current": _Field(list, required=False, elem_type=dict),
    "power_loss": _Field(dict, required=False),
}
# parts-0004: `[function.operating]` names the model's `Operating` fields: figure lists and quantity strings
OPERATING_FIGURES = {"voltage": Unit.V, "max_current": Unit.A, "fault_current": Unit.A}
OPERATING_QUANTITIES = {
    "fault_time_constant": Unit.MS,
    "capacity": Unit.AH,
    "resistance": Unit.OHM,
    "nominal_power": Unit.W,
    "nominal_current": Unit.A,
}
OPERATING_FIELDS = {key: _Field(list, required=False, elem_type=dict) for key in OPERATING_FIGURES} | {
    key: _Field(str, required=False) for key in OPERATING_QUANTITIES
}


def block_figures(table: object) -> Spec:
    """The breaking-figure fields a `[function.block]` may state: its `type` decides."""
    kind = table.get("type") if isinstance(table, dict) else None
    return _BREAKING.get(kind, {}) if type(kind) is str else {}


def check_fields(table: object, spec: dict[str, _Field], *, path: str, line: int, table_name: str) -> list[Finding]:
    """`FIELD_UNKNOWN`, `FIELD_MISSING`, `FIELD_TYPE`, `FLOAT_FORBIDDEN`, `ENUM_VALUE`."""
    loc = _Loc(path=path, line=line, table_name=table_name)
    if not isinstance(table, dict):  # isinstance, not `type(...) is`: ty narrows only this to dict
        return [_toml.finding("FIELD_TYPE", loc.path, loc.line, f"{loc.table_name} must be a table")]
    findings = [_toml.finding("FIELD_UNKNOWN", loc.path, loc.line, f"{loc.table_name} has no field {key!r}") for key in table if key not in spec]
    for name, field in spec.items():
        findings.extend(_check_field(table, name, field, loc))
    return findings


def _check_field(table: dict[str, Any], name: str, field: _Field, loc: _Loc) -> list[Finding]:
    if name not in table:
        if not field.required:
            return []
        text = f"{loc.table_name} is missing {name!r}"
        return [_toml.finding("FIELD_MISSING", loc.path, loc.line, text)]
    return _check_present_field(table[name], name, field, loc)


def _check_present_field(value: object, name: str, field: _Field, loc: _Loc) -> list[Finding]:
    if type(value) is Decimal:
        # A bare TOML float anywhere in the file is `_toml.value_findings`' job
        # ("anywhere ... in an unknown table or field too"), so this field is skipped here rather
        # than reported a second time.
        return []
    if field.enum is not None:
        return _check_enum(value, field.enum, loc, name)
    if type(value) is not field.type_:
        text = f"{loc.table_name}.{name} must be {field.type_.__name__}, not {type(value).__name__}"
        return [_toml.finding("FIELD_TYPE", loc.path, loc.line, text)]
    if field.elem_type is not None and type(value) is list and any(type(item) is not field.elem_type for item in value):
        text = f"{loc.table_name}.{name} entries must all be {field.elem_type.__name__}"
        return [_toml.finding("FIELD_TYPE", loc.path, loc.line, text)]
    return []


def _check_enum(value: object, enum_cls: type[Enum] | Mapping[str, object], loc: _Loc, name: str) -> list[Finding]:
    if type(value) is not str:
        return [_toml.finding("FIELD_TYPE", loc.path, loc.line, f"{loc.table_name}.{name} must be a string")]
    words = list(enum_cls) if isinstance(enum_cls, Mapping) else [m.value if isinstance(m.value, str) else m.name.lower() for m in enum_cls]
    if value not in words:
        members = ", ".join(repr(w) for w in words)
        return [
            _toml.finding(
                "ENUM_VALUE",
                loc.path,
                loc.line,
                f"{loc.table_name}.{name} must be one of {members}, not {value!r}",
            )
        ]
    return []
