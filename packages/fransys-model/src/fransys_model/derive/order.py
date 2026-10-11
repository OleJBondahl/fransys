"""The one module of reader-order keys: natural designation order, bom lines, lists (model-0189).

Reached as `fransys_model.derive.order.<name>`; `derive/__init__.py` re-exports only the names
`derive.__all__` already held. A key over a printed designation needs the model, so it lives here,
above `vocab`, whose `marking_key` stays the text primitive.
"""

from typing import TYPE_CHECKING, Any

from fransys_model.derive.designation import (
    item_designation,
    port_designation,
    terminal_of,
)
from fransys_model.kernel import Finding, Id, Model, SchemaError
from fransys_model.vocab import marking_key
from fransys_model.vocab.tables import items
lazy from fransys_model.vocab.core import Item

if TYPE_CHECKING:
    from collections.abc import Iterable


__all__ = [
    "NaturalKey",
    "bom_sort_key",
    "designation_key",
    "finding_order_key",
    "in_designation_order",
    "natural_key",
]

type NaturalKey = tuple[tuple[tuple[int, int, str], ...], str]


def natural_key(text: str) -> NaturalKey:
    """Sort key of a printed text: digit runs by value, so `-W2` sorts before `-W10`.

    Text runs compare as strings and sort after numbers; the whole text breaks a tie.
    """
    return marking_key(text), text


def designation_key(model: Model, item: Id[Item]) -> NaturalKey:
    """`natural_key` of `item`'s printed designation: the one spelling of "by designation"."""
    return natural_key(item_designation(model, item))


def in_designation_order(model: Model, listed: Iterable[Id[Item]]) -> tuple[Id[Item], ...]:
    """`listed` sorted by `natural_key` of its designation (`-X2` before `-X10`), then id."""
    return tuple(sorted(listed, key=lambda item: (designation_key(model, item), item)))


def bom_sort_key(model: Model, item: Id[Item]) -> tuple[int, NaturalKey, str, int]:
    """Sort key for one item within a `bom_lines` line's `designations`.

    A terminal with a parent sorts `(0, its strip's item_designation, its own group, its own
    index)`: by strip, then group, then index. `group`/`index` come straight off the
    `TerminalFacet`, never re-parsed from rendered text, so `"L1:10"` sorts after `"L1:2"`. Any
    other item sorts
    `(1, natural_key(its own item_designation), "", 0)`: digit runs by value (`-K2`, `-K10`).

    Raises:
        SchemaError: as `item_designation`.
    """
    record = items(model).get(item)
    t = terminal_of(model, item)
    if record is not None and record.parent is not None and t is not None:
        return (0, designation_key(model, record.parent), t.group, t.index)
    return (1, designation_key(model, item), "", 0)


def _printed(model: Model, subject: Id[Any]) -> str | None:
    """The subject's printed designation, or `None` for a kind that prints none or cannot."""
    try:
        if subject.kind == "item":
            return item_designation(model, subject)
        if subject.kind == "port":
            return port_designation(model, subject)
    except SchemaError:  # an unnumbered item or strip: the numbering finding names it
        return None
    return None


def finding_order_key(model: Model, finding: Finding) -> tuple[int, NaturalKey | tuple[()]]:
    """Sort key of one finding within its code: natural order of its first subject's designation.

    A finding whose first subject prints no designation sorts after those that do (O8).
    """
    text = _printed(model, finding.subjects[0]) if finding.subjects else None
    return (1, ()) if text is None else (0, natural_key(text))
