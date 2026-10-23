"""A tag echo's text and a reference's digit count, on plain values (layout-0089, layout-0135).

The layout engines pass the values (a partner's set rank, page, column and position text; a set's
reference count) and print what these return.
"""

lazy from collections.abc import Iterable

from fransys_model.derive.order import echo_entry_key

__all__ = ["reference_digits", "tag_echo_text"]

#: One partner of a tag echo: its set rank, page and frame column, then the position text.
EchoEntry = tuple[int, int, int, str]


def tag_echo_text(entries: Iterable[EchoEntry]) -> str:
    """The partners' position texts, each once, in `echo_entry_key` order, joined by a space."""
    return " ".join(entry[3] for entry in sorted(set(entries), key=echo_entry_key))


def reference_digits(count: int, *, floor: int = 2) -> int:
    """The digits a `#n` is sized for: those of the set's highest number, `floor` at least."""
    digits = len(str(count))
    return max(floor, digits)
