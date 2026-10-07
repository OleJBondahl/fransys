"""The breaking-point lists of a `[rating]` table: `breaking_ac` and `breaking_dc` (parts-0015).

Each is a list of inline tables `{ voltage_v, current_a, time_constant_ms }` of decimal strings.
A malformed list or point is `RATING_VALUE_INVALID`, naming the field and the point index.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from fransys_model.vocab import BreakingPoint

from . import _toml

if TYPE_CHECKING:
    from collections.abc import Callable

    from fransys_model.kernel import Finding

POINT_FIELDS = ("breaking_ac", "breaking_dc")
_REQUIRED = ("voltage_v", "current_a")
_KEYS = (*_REQUIRED, "time_constant_ms")


def check_points(
    field: object,
    value: object,
    *,
    is_plain: Callable[[str], bool],
    at: tuple[str, int],
    name: str,
) -> list[Finding]:
    """Findings for one point list; `is_plain(text)` is the positive-decimal rule."""
    if not isinstance(value, list):
        return []  # FIELD_TYPE from `_fields`
    where = f"{name}.{field}"
    if not value:
        texts = [f"{where} must hold at least one point, not an empty list"]
    else:
        texts = [
            f"{where}[{index}]{problem}"
            for index, point in enumerate(value)
            for problem in _point_problems(field, point, is_plain)
        ]
    return [_toml.finding("RATING_VALUE_INVALID", at[0], at[1], text) for text in texts]


def _point_problems(field: object, point: object, is_plain: Callable[[str], bool]) -> list[str]:
    if not isinstance(point, dict):
        return [' must be a table such as { voltage_v = "1000", current_a = "15000" }']
    problems = [f" has no key {key!r}" for key in _REQUIRED if key not in point]
    problems += [f" has unknown key {key!r}" for key in point if key not in _KEYS]
    if field == "breaking_ac" and "time_constant_ms" in point:
        problems.append(".time_constant_ms is for a breaking_dc point only")
        point = {k: v for k, v in point.items() if k != "time_constant_ms"}
    problems += [
        f'.{key} must be a positive number such as "15", not {point[key]!r}'
        for key in _KEYS
        if key in point
        and type(point[key]) is not Decimal  # a bare float is FLOAT_FORBIDDEN, reported by `_toml`
        and not (type(point[key]) is str and is_plain(point[key]))
    ]
    return problems


def build_points(points: list[dict[str, str]]) -> tuple[BreakingPoint, ...]:
    """The `BreakingPoint` tuple of a lint-clean point list."""
    return tuple(
        BreakingPoint(
            voltage_v=Decimal(p["voltage_v"]),
            current_a=Decimal(p["current_a"]),
            time_constant_ms=Decimal(p["time_constant_ms"]) if "time_constant_ms" in p else None,
        )
        for p in points
    )
