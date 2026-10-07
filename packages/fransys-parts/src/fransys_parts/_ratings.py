"""The rating tables of a part file: `[rating]`, `[function.rating]`, `[function.operating]`.

Decision parts-0004. Lint and loader share this module so the table names, the value rule and
the record building have one home. Finding codes emitted here:

- `RATING_TABLE_EMPTY`: a rating or operating table with no field.
- `RATING_VALUE_INVALID`: a string value that is not a number in plain decimal notation, or
  is zero where the table needs a positive one. Plain notation is digits with an optional
  fractional part (`"250"`, `"0.5"`); an exponent, a sign (so no negative), a space, a
  separator, `NaN` and `Infinity` are refused. A `[rating]` or `[function.rating]` value must
  be above zero; a `[function.operating]` value may be zero (parts-0006), as a source's
  `min_voltage_v` may be 0.

- `RATING_VALUE_INVALID` also covers a malformed `breaking_ac` or `breaking_dc` point list
  (parts-0015, `_breaking_points`): empty, a non-table entry, a missing or unknown key, a
  non-positive value, or a `time_constant_ms` on an AC point.

A value that is not a string is `FIELD_TYPE` (or `FLOAT_FORBIDDEN`) from `_fields`/`_toml`,
and is not reported again here.
"""

import re
from decimal import Decimal
from typing import Any

from fransys_model.kernel import Draft, Finding, Id, Origin, make_id
from fransys_model.vocab import (
    FunctionTemplate,
    Operating,
    OperatingFacet,
    Part,
    PartRatingFacet,
    Rating,
    RatingFacet,
)

from . import _breaking_points, _fields, _toml

_PLAIN_DECIMAL = re.compile(r"[0-9]+(\.[0-9]+)?")


def _check_table(
    table: object,
    spec: _fields.Spec,
    *,
    at: tuple[str, int],
    name: str,
    allow_zero: bool,
) -> list[Finding]:
    """Check one table; `at` is the (file, line) its findings are reported at."""
    path, line = at
    findings = _fields.check_fields(table, spec, path=path, line=line, table_name=name)
    if type(table) is not dict:
        return findings
    if not table:
        text = f"{name} has no field; give at least one value or drop the table"
        return [*findings, _toml.finding("RATING_TABLE_EMPTY", path, line, text)]
    expected = 'a number of 0 or more such as "24" or "0.5"'
    if not allow_zero:
        expected = 'a positive number such as "24" or "0.5"'
    for field, value in table.items():
        if field in _breaking_points.POINT_FIELDS and field in spec:
            findings.extend(
                _breaking_points.check_points(
                    field,
                    value,
                    is_plain=lambda text: _is_plain_decimal(text, allow_zero=False),
                    at=at,
                    name=name,
                )
            )
        elif (
            field in spec
            and type(value) is str
            and not _is_plain_decimal(value, allow_zero=allow_zero)
        ):
            text = f"{name}.{field} must be {expected}, not {value!r}"
            findings.append(_toml.finding("RATING_VALUE_INVALID", path, line, text))
    return findings


def _is_plain_decimal(value: str, *, allow_zero: bool) -> bool:
    if _PLAIN_DECIMAL.fullmatch(value) is None:
        return False
    return allow_zero or Decimal(value) > 0


def check_part_rating(data: _toml.Table, path: str, origins: _toml.Origins) -> list[Finding]:
    """Check a top-level `[rating]`; nothing when the file has none."""
    if "rating" not in data:
        return []
    line = origins.get(("rating",), 1)
    return _check_table(
        data["rating"], _fields.RATING_FIELDS, at=(path, line), name="rating", allow_zero=False
    )


def check_function_tables(
    entry: _toml.Table, path: str, origins: _toml.Origins, index: int, function_line: int
) -> list[Finding]:
    """Check the rating and operating tables of function `index` (inline: `function_line`)."""
    findings: list[Finding] = []
    for table_name, spec, allow_zero in (
        ("rating", _fields.RATING_FIELDS, False),
        ("operating", _fields.OPERATING_FIELDS, True),
    ):
        if table_name in entry:
            line = origins.get(("function", index, table_name), function_line)
            findings.extend(
                _check_table(
                    entry[table_name],
                    spec,
                    at=(path, line),
                    name=f"function.{table_name}",
                    allow_zero=allow_zero,
                )
            )
    return findings


def add_part_rating(
    draft: Draft, table: _toml.Table, part_id: Id[Part], part_key: tuple[str, ...], origin: Origin
) -> None:
    """Add the `PartRatingFacet` of a lint-clean `[rating]` table."""
    key = (*part_key, "rating")
    facet = PartRatingFacet(
        id=make_id(PartRatingFacet, key), key=key, subject=part_id, rating=_rating(table)
    )
    draft.add(facet, origin=origin)


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
        rating_facet = RatingFacet(
            id=make_id(RatingFacet, key),
            key=key,
            subject=function_id,
            rating=_rating(entry["rating"]),
        )
        draft.add(rating_facet, origin=origin_of["rating"])
    if "operating" in entry:
        key = (*function_key, "operating")
        operating_facet = OperatingFacet(
            id=make_id(OperatingFacet, key),
            key=key,
            subject=function_id,
            operating=Operating(**{k: Decimal(v) for k, v in entry["operating"].items()}),
        )
        draft.add(operating_facet, origin=origin_of["operating"])


def _rating(table: _toml.Table) -> Rating:
    values: dict[str, Any] = {
        k: _breaking_points.build_points(v) if k in _breaking_points.POINT_FIELDS else Decimal(v)
        for k, v in table.items()
    }
    return Rating(**values)
