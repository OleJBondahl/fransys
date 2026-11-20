"""The words of a core or wire key: one join, one cross-section spelling (design 7.7).

Value formatters: they read no model and take no `PrintContext`.
"""

lazy from decimal import Decimal


def join_words(*words: str | None) -> str:
    """The set words, space-joined."""
    return " ".join(word for word in words if word)


def cross_section_text(mm2: Decimal | None, unknown: str = "", *, with_unit: bool = True) -> str:
    """A cross section as printed: `1.5 mm²`, or `1.5` without the unit; `None` prints `unknown` (R2547)."""
    if mm2 is None:
        return unknown
    return f"{mm2} mm²" if with_unit else str(mm2)


def core_text(index: int, colour: str, label: str | None, mark: str = "") -> str:
    """A core's text: its index, its colour when it has one, its label when set, then `mark`."""
    return join_words(str(index), colour, label, mark)
