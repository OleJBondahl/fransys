"""The words of a core or wire key: one join, one cross-section spelling (design 7.7).

Value formatters: they read no model and take no `PrintContext`.
"""

lazy from decimal import Decimal


def join_words(*words: str | None) -> str:
    """The set words, space-joined."""
    return " ".join(word for word in words if word)


def cross_section_text(mm2: Decimal) -> str:
    """A cross section as printed: `1.5 mm²`."""
    return f"{mm2} mm²"


def core_text(index: int, colour: str, label: str | None, mark: str = "") -> str:
    """A core's text: its index, its colour when it has one, its label when set, then `mark`."""
    return join_words(str(index), colour, label, mark)
