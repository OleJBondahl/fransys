"""Reading canonical JSON text into frozendicts, tuples and primitives (kernel-model.md 5.6)."""

import json

from .errors import SchemaError

_KIND = "canonical"


def read_json(text: str) -> object:
    """Parse canonical JSON into frozendicts, tuples and primitives.

    Refuses a repeated key, a fraction or exponent (a `Decimal` is a string), `NaN`, `Infinity`.
    Raises `SchemaError` for text that is not valid canonical JSON or is nested too deeply.
    """
    try:
        parsed = json.loads(
            text,
            object_pairs_hook=_no_duplicates,
            parse_int=_read_int,
            parse_float=_refuse_float,
            parse_constant=_refuse_constant,
        )
        return _thaw(parsed)
    except json.JSONDecodeError as exc:
        msg = f"not valid JSON: {exc}"
        raise SchemaError(msg, kind=_KIND) from exc
    except RecursionError as exc:
        msg = "the JSON is nested too deeply"
        raise SchemaError(msg, kind=_KIND) from exc


def _no_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    keys = [key for key, _ in pairs]
    if len(set(keys)) != len(keys):
        repeated = sorted({key for key in keys if keys.count(key) > 1})
        msg = f"duplicate key in one object: {repeated}"
        raise SchemaError(msg, kind=_KIND)
    return dict(pairs)


def _read_int(text: str) -> int:
    try:
        return int(text)
    except ValueError as exc:  # CPython's limit on the digits of an int
        msg = f"an integer of {len(text)} characters cannot be read"
        raise SchemaError(msg, kind=_KIND) from exc


def _refuse_float(text: str) -> object:
    msg = f"the number {text} has a fraction or an exponent: canonical JSON has no such numbers"
    raise SchemaError(msg, kind=_KIND)


def _refuse_constant(text: str) -> object:
    msg = f"{text} is not canonical JSON"
    raise SchemaError(msg, kind=_KIND)


def _thaw(value: object) -> object:
    if isinstance(value, dict):
        return frozendict({key: _thaw(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_thaw(item) for item in value)
    return value
