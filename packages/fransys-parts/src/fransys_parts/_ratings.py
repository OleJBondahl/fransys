"""The figure tables of a schema 2 part file.

They are `[rating]`, `[function.rating]`, `[function.operating]` and the breaking figures of
`[function.block]` (decisions parts-0004, model-0369, model-0381).

One reader for lint and loader. A figure is an elecdef `Range` written as an inline table
`{ role, min, nom, typ, max, at }`; a quantity is the string `"24 V"` (number, space, unit symbol),
the symbol looked up in `elecdef.Unit`; `at` lists `"AC"`, `"DC"` or a quantity such as
`"250 V"` or `"5 ms"`. A rating is an elecdef `Rating`, a fuse's `breaking_capacity` an elecdef `Fuse`,
an mcb's `icn`, `icu`, `ics` an elecdef `Breaker`. Finding codes emitted here:

- `RATING_TABLE_EMPTY`: a rating or operating table with no field.
- `RATING_VALUE_INVALID`: a figure or quantity the reader refuses, with the reason.
- `POWER_LOSS_TWICE`: `power_loss` in `[rating]` and in some `[function.rating]`.
"""

import re
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from fransys_model.elecdef import At, Block, Breaker, Current, Fuse, Quantity, Range, Rating, Role, Unit
from fransys_model.kernel import Draft, Finding, Id, Origin, make_id
from fransys_model.vocab import (
    BlockFacet,
    FunctionTemplate,
    Operating,
    OperatingFacet,
    Part,
    PartRatingFacet,
    RatingFacet,
)

from . import _fields, _toml
from ._errors import PartTextError

if TYPE_CHECKING:
    from collections.abc import Callable

_PLAIN = re.compile(r"[0-9]+(\.[0-9]+)?")
_UNITS = {unit.symbol: unit for unit in Unit}
_ENDS = ("min", "nom", "typ", "max")
_FAULTS = (KeyError, TypeError, ValueError, PartTextError)


def _quantity(text: object, *, zero: bool = False) -> Quantity:
    number, _, symbol = str(text).partition(" ")
    if type(text) is not str or _PLAIN.fullmatch(number) is None or symbol not in _UNITS:
        msg = f'{text!r} is not a quantity such as "24 V"'
        raise PartTextError(msg)
    if not zero and Decimal(number) == 0:
        msg = f"{text!r} must be above zero"
        raise PartTextError(msg)
    return Quantity(Decimal(number), _UNITS[symbol])


def _range(table: object, *, zero: bool = False) -> Range:
    if not isinstance(table, dict):
        msg = 'a figure is an inline table such as { nom = "24 V" }'
        raise PartTextError(msg)
    if unknown := next((key for key in table if key not in {"role", "at", *_ENDS}), None):
        msg = f"a figure has no key {unknown!r}"
        raise PartTextError(msg)
    ends = {key: _quantity(table[key], zero=zero) for key in _ENDS if key in table}
    at = At(*(Current[c] if c in ("AC", "DC") else _quantity(c) for c in table.get("at", ())))
    return Range(Role[str(table.get("role", "rated")).upper()], at=at, **ends)


def _breaking_point(item: object) -> Range:
    """A breaking figure: without a voltage it states min; with one it is at AC, or at DC with a time constant."""
    figure = _range(item)
    if figure.at.get(Unit.V.kind) is None:
        if figure.min is None:
            msg = "a breaking figure without a voltage states min (the lowest current broken)"
            raise PartTextError(msg)
    elif (current := figure.at.get(Current)) is None or (current is Current.AC and figure.at.get(Unit.MS.kind) is not None):
        msg = 'a breaking point is stated at "AC", or at "DC" with an optional time constant'
        raise PartTextError(msg)
    return figure


def parse_rating(table: _toml.Table) -> Rating:
    """The elecdef `Rating` of a `rating` table."""
    return Rating(
        voltage=tuple(map(_range, table.get("voltage", ()))),
        current=tuple(map(_range, table.get("current", ()))),
        power_loss=_range(table["power_loss"]) if "power_loss" in table else None,
    )


def parse_block(table: _toml.Table) -> Block | None:
    """The `Fuse` or `Breaker` of a block's breaking figures; None when it states none."""
    if table.get("type") == "fuse":
        figures = tuple(map(_breaking_point, table.get("breaking_capacity", ())))
        return Fuse(breaking_capacity=figures) if figures else None
    breaker = {key: _breaking_point(table[key]) for key in _fields.BREAKER_KEYS if key in table}
    return Breaker(icn=breaker.get("icn"), icu=breaker.get("icu"), ics=breaker.get("ics")) if breaker else None


def _checked(unit: Unit, key: str, value: Quantity | Range) -> None:
    kind = value.unit.kind if isinstance(value, Quantity) else value.kind
    if kind is not unit.kind:
        msg = f"{key} takes a {unit.kind.name.lower()} value, not {kind.name.lower()}"
        raise PartTextError(msg)


def parse_operating(table: _toml.Table) -> Operating:
    """The model `Operating` of an `operating` table; each field is checked for its unit kind."""
    values: dict[str, Any] = {}
    for key, unit in _fields.OPERATING_FIGURES.items():
        values[key] = tuple(_range(item, zero=True) for item in table.get(key, ()))
        for figure in values[key]:
            _checked(unit, key, figure)
    for key, unit in _fields.OPERATING_QUANTITIES.items():
        if key in table:
            values[key] = _quantity(table[key], zero=True)
            _checked(unit, key, values[key])
    return Operating(**values)


def _has_float(value: object) -> bool:
    """A bare TOML float anywhere inside `value`; `_toml.value_findings` reports it once."""
    if isinstance(value, dict):
        value = list(value.values())
    return type(value) is Decimal or (isinstance(value, list) and any(map(_has_float, value)))


def _check_table(
    table: object,
    spec: _fields.Spec,
    build: Callable[[_toml.Table], object],
    *,
    at: tuple[str, int],
    name: str,
) -> list[Finding]:
    """Check one table; `at` is the (file, line) its findings are reported at."""
    path, line = at
    findings = _fields.check_fields(table, spec, path=path, line=line, table_name=name)
    if not isinstance(table, dict):
        return findings
    if not table:
        text = f"{name} has no field; give at least one value or drop the table"
        return [*findings, _toml.finding("RATING_TABLE_EMPTY", path, line, text)]
    if not findings and not _has_float(table):
        try:
            build(table)
        except _FAULTS as error:
            text = f"{name}: {error.args[0] if error.args else error!r}"
            findings.append(_toml.finding("RATING_VALUE_INVALID", path, line, text))
    return findings


def check_part_rating(data: _toml.Table, path: str, origins: _toml.Origins) -> list[Finding]:
    """Check a top-level `[rating]` and the power-loss rule; nothing when the file has none."""
    if "rating" not in data:
        return []
    line = origins.get(("rating",), 1)
    findings = _check_table(data["rating"], _fields.RATING_FIELDS, parse_rating, at=(path, line), name="rating")
    functions = data.get("function")
    if type(data["rating"]) is not dict or "power_loss" not in data["rating"]:
        return findings
    return findings + [
        _toml.finding(
            "POWER_LOSS_TWICE",
            path,
            origins.get(("function", index), 1),
            f"function {entry.get('name')!r} states power_loss and so does the part's [rating]: state it once, or a heat sum counts it twice",
        )
        for index, entry in enumerate(functions if type(functions) is list else [])
        if isinstance(entry, dict) and isinstance(entry.get("rating"), dict) and "power_loss" in entry["rating"]
    ]


def check_function_tables(entry: _toml.Table, path: str, origins: _toml.Origins, index: int, function_line: int) -> list[Finding]:
    """Check the rating and operating tables and the breaking list of function `index`."""
    findings: list[Finding] = []
    block = entry.get("block")
    for table_name, spec, build in (
        ("rating", _fields.RATING_FIELDS, parse_rating),
        ("operating", _fields.OPERATING_FIELDS, parse_operating),
    ):
        if table_name in entry:
            line = origins.get(("function", index, table_name), function_line)
            at = (path, line)
            name = f"function.{table_name}"
            findings.extend(_check_table(entry[table_name], spec, build, at=at, name=name))
    return [*findings, *_check_block(block, (path, origins.get(("function", index, "block"), function_line)), "function.block")]


def _check_block(block: object, at: tuple[str, int], name: str) -> list[Finding]:
    """Check the breaking figures of a block table; its other fields are `check_protection_type`'s."""
    spec = _fields.block_figures(block)
    if not isinstance(block, dict) or not (figures := {key: block[key] for key in block if key in spec}):
        return []
    return _check_table(figures, spec, lambda t: parse_block({**t, "type": block["type"]}), at=at, name=name)


def check_part_block(data: _toml.Table, path: str, origins: _toml.Origins) -> list[Finding]:
    """Check a top-level `[block]`, a fuse link's breaking figures; nothing when the file has none."""
    if "block" not in data:
        return []
    at = (path, origins.get(("block",), 1))
    templates = len(data.get("function", ()))
    if templates != 1:
        part = data.get("part", {}).get("mpn", "?")
        text = f"part {part} has {templates} functions: a part-level [block] is the block of a part's one function; state [block] per pole"
        return [_toml.finding("RATING_VALUE_INVALID", path, at[1], text)]
    fields = _fields.check_fields(
        data["block"], _fields.BLOCK_FIELDS | _fields.block_figures(data["block"]), path=path, line=at[1], table_name="block"
    )
    return [*fields, *_check_block(data["block"], at, "block")]


def add_part_rating(draft: Draft, table: _toml.Table, part_id: Id[Part], part_key: tuple[str, ...], origin: Origin) -> None:
    """Add the `PartRatingFacet` of a lint-clean `[rating]` table."""
    key = (*part_key, "rating")
    facet = PartRatingFacet(id=make_id(PartRatingFacet, key), key=key, subject=part_id, rating=parse_rating(table))
    draft.add(facet, origin=origin)


def add_part_block(draft: Draft, data: _toml.Table, part_key: tuple[str, ...], path: str, origins: _toml.Origins) -> None:
    """Add the `BlockFacet` of a lint-clean part-level `[block]` that states a figure: the block of the part's one template."""
    if "block" in data and (block := parse_block(data["block"])) is not None:
        function_key = (*part_key, "function", data["function"][0]["name"])
        key = (*function_key, "block")
        origin = Origin(file=path, line=origins.get(("block",), 1), note="")
        draft.add(BlockFacet(id=make_id(BlockFacet, key), key=key, subject=make_id(FunctionTemplate, function_key), block=block), origin=origin)


def add_function_tables(
    draft: Draft,
    entry: _toml.Table,
    function_id: Id[FunctionTemplate],
    function_key: tuple[str, ...],
    origin_of: dict[str, Origin],
) -> None:
    """Add a function entry's rating and operating facets, each at its table's origin."""
    if "rating" in entry:
        key = (*function_key, "rating")
        facet = RatingFacet(id=make_id(RatingFacet, key), key=key, subject=function_id, rating=parse_rating(entry["rating"]))
        draft.add(facet, origin=origin_of["rating"])
    if (block := parse_block(entry.get("block", {}))) is not None:
        key = (*function_key, "block")
        draft.add(BlockFacet(id=make_id(BlockFacet, key), key=key, subject=function_id, block=block), origin=origin_of["block"])
    if "operating" in entry:
        key = (*function_key, "operating")
        operating = parse_operating(entry["operating"])
        operating_facet = OperatingFacet(id=make_id(OperatingFacet, key), key=key, subject=function_id, operating=operating)
        draft.add(operating_facet, origin=origin_of["operating"])
