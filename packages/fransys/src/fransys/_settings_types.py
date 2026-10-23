"""The type rule of a consumer's settings value against ours (SETTINGS-OPEN SO1)."""

from collections.abc import Mapping


def type_word(ours: object) -> str:
    """The word the refusal message uses for the type of our value."""
    if isinstance(ours, bool):
        return "true or false"
    if isinstance(ours, Mapping):
        return "a table"
    words = {int: "a whole number", float: "a number", str: "text", list: "a list"}
    return next((word for kind, word in words.items() if isinstance(ours, kind)), "a value")


def _fits_list(ours: list[object], value: object) -> bool:
    if not isinstance(value, list):
        return False
    if len({type(e) for e in ours}) > 1:  # mixed types: a fixed-shape record, element by element
        return len(value) == len(ours) and all(fits(o, v) for o, v in zip(ours, value, strict=True))
    return not ours or all(fits(ours[0], v) for v in value)


def fits(ours: object, value: object) -> bool:
    """Whether `value` has the type of `ours`; no range check.

    An int fits a float, a bool only a bool. A mixed-type list is a fixed-shape record, else a list
    fits its first element in any length.
    """
    if isinstance(ours, bool) or isinstance(value, bool):
        return isinstance(ours, bool) and isinstance(value, bool)
    if isinstance(ours, float):
        return isinstance(value, int | float)
    if isinstance(ours, list):
        return _fits_list(ours, value)
    return isinstance(value, type(ours))
