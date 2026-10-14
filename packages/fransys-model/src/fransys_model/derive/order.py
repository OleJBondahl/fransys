"""The one module of reader-order keys: natural designation order, bom lines, lists (model-0189).

Reached as `fransys_model.derive.order.<name>`; `derive/__init__.py` re-exports only the names
`derive.__all__` already held. A key over a printed designation needs the model, so it lives here,
above `vocab`, whose `marking_key` stays the text primitive.
"""

from typing import TYPE_CHECKING, Any, Protocol

from fransys_model.derive.designation import (
    function_designation,
    item_designation,
    port_designation,
    terminal_of,
)
from fransys_model.derive.lookups import position_rank
from fransys_model.derive.plc_rack import is_plc_module
from fransys_model.kernel import Finding, Id, Model, SchemaError
from fransys_model.layout import DrawingSet, HarnessLine, Page, layout_of, page_slice
from fransys_model.vocab import marking_key
from fransys_model.vocab.tables import items
lazy from fransys_model.vocab.core import Function, Item, Unit

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence


__all__ = [
    "NaturalKey",
    "bom_sort_key",
    "by_place",
    "designation_key",
    "drawn_lines_on_page",
    "drawn_on_page",
    "finding_order_key",
    "in_designation_order",
    "natural_key",
    "plc_channel_key",
    "plc_racks",
    "wire_run",
]


class _Placed(Protocol):
    """A record with a place on a page."""

    @property
    def x(self) -> int: ...

    @property
    def y(self) -> int: ...


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


def plc_racks(model: Model) -> frozenset[Id[Item]]:
    """The racks: every item with a `PLC_MODULE` child (`is_plc_module`)."""
    return frozenset(
        one.parent
        for one in items(model).values()
        if one.parent is not None and is_plc_module(model, one)
    )


def plc_channel_key(
    model: Model, racks: frozenset[Id[Item]], item: Id[Item], number: int, function: Id[Function]
) -> tuple[int, NaturalKey, int, tuple[int, int], tuple[str, ...], int, Id[Function]]:
    """Sort key of a PLC channel: the one order of the PLC list's tables and rows (model-0194).

    Racks by designation; in a rack its own channels, then each module in `plc_rack_modules` order
    (`position`, authoring key); channels by `(number, function id)`. Last come the channels on
    an item in no rack, by item designation. `racks` is `plc_racks(model)`.
    """
    record = items(model)[item]
    tail = (number, function)
    if item in racks:
        return (0, designation_key(model, item), 0, (0, 0), (), *tail)
    if record.parent in racks and is_plc_module(model, record):
        rack = record.parent
        return (0, designation_key(model, rack), 1, position_rank(record), record.key, *tail)
    return (1, designation_key(model, item), 0, (0, 0), (), *tail)


def by_place[T: _Placed](
    drawn: Iterable[T], local: Callable[[T], NaturalKey] | None = None
) -> tuple[T, ...]:
    """`drawn` top-down, left to right; a tie breaks on `local`, then on the order it came in.

    A page draws its symbols, labels and markers in this order, so no id (which follows the
    instance path) decides which is drawn first. `local` is the thing's designation as printed
    within its unit (`_local_designation`), never the instance tag.
    """
    if local is None:
        return tuple(sorted(drawn, key=lambda one: (one.y, one.x)))
    return tuple(sorted(drawn, key=lambda one: (one.y, one.x, local(one))))


def _local_designation(model: Model, record: object, unit: Id[Unit] | None) -> NaturalKey:
    """`natural_key` of the designation `record` prints in `unit`'s own document, else of `""`.

    A record names a `port`, a `function` or a `harness`; one that names none, or an item that
    prints none, keys as the empty text.
    """
    try:
        if (port := getattr(record, "port", None)) is not None:
            return natural_key(port_designation(model, port, unit=unit))
        if (function := getattr(record, "function", None)) is not None:
            return natural_key(function_designation(model, function, unit=unit))
        if (harness := getattr(record, "harness", None)) is not None:
            return natural_key(item_designation(model, harness, unit=unit))
    except SchemaError:  # an item that prints no designation: the numbering finding names it
        pass
    return natural_key("")


def drawn_on_page[R: _Placed](model: Model, record_type: type[R], page: Page) -> tuple[R, ...]:
    """The page's `record_type` records in drawn order: `by_place`, then the local designation."""
    unit = layout_of(model, DrawingSet)[page.drawing_set].unit
    return by_place(
        page_slice(model, record_type, page), lambda one: _local_designation(model, one, unit)
    )


def drawn_lines_on_page(model: Model, page: Page) -> tuple[HarnessLine, ...]:
    """The page's harness lines by `wire_run` of their points, then the harness designation."""
    unit = layout_of(model, DrawingSet)[page.drawing_set].unit
    return tuple(
        sorted(
            page_slice(model, HarnessLine, page),
            key=lambda line: (
                wire_run([(point.x, point.y) for point in line.points]),
                _local_designation(model, line, unit),
            ),
        )
    )


def wire_run(points: Sequence[tuple[int, int]]) -> tuple[tuple[int, int], ...]:
    """A drawn wire's `(x, y)` points read from its upper end, then its left one.

    The run is also the wire's order key: wires draw top-down, left to right, from their own
    ends, so a name above the unit (an id) never picks the end or the place.
    """
    run = tuple(points)
    return min(run, run[::-1], key=lambda way: (way[0][1], way[0][0], way[-1][1], way[-1][0]))


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
    """Sort key of one finding within its code: natural order of its first printing subject.

    Subjects are stored in `Id` order, so the first one may be a facet that prints nothing; the
    key reads the first subject that prints a designation. A finding with none sorts after those
    that do.
    """
    text = next((one for s in finding.subjects if (one := _printed(model, s)) is not None), None)
    return (1, ()) if text is None else (0, natural_key(text))
