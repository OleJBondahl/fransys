"""The one module of reader-order keys: natural designation order, bom lines, lists (model-0189).

Reached as `fransys_model.derive.order.<name>`; `derive/__init__.py` re-exports only the names
`derive.__all__` already held. A key over a printed designation needs the model, so it lives here,
above `vocab`; the text key itself is the kernel's `natural_key` (NUMBER-SORT K7).
"""

from typing import TYPE_CHECKING, Any, Protocol

from fransys_model.derive.designation import (
    function_designation,
    item_designation,
    port_designation,
)
from fransys_model.derive.designation_label import terminal_of
from fransys_model.derive.facts.children import child_items
from fransys_model.derive.facts.item_predicates import is_plc_module
from fransys_model.derive.facts.subjects import subject_kind
from fransys_model.derive.instance_tag import instance_name, instance_tags
from fransys_model.derive.lookups import position_rank
from fransys_model.kernel import (
    DIGEST_CACHE_SIZE,
    AuthoringKey,
    Finding,
    Id,
    Model,
    NaturalKey,
    SchemaError,
    digest_cached,
    natural_key,
)
from fransys_model.layout import DrawingSet, OrderHint, Page, layout_of, page_slice
from fransys_model.vocab.enums import SubjectKind
from fransys_model.vocab.tables import aspect_nodes, items
lazy from fransys_model.derive.rows_series_parallel import SeriesRowPart
lazy from fransys_model.vocab.aspects import AspectNode
lazy from fransys_model.vocab.connectivity import Conductor
lazy from fransys_model.vocab.core import Function, Item, Port, Unit

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping


__all__ = [
    "NaturalKey",
    "bom_sort_key",
    "by_place",
    "designation_key",
    "drawn_on_page",
    "echo_entry_key",
    "finding_order_key",
    "findings_in_order",
    "in_designation_order",
    "location_key",
    "locations_in_order",
    "natural_key",
    "order_hint_key",
    "plc_channel_key",
    "plc_channel_tie",
    "plc_module_key",
    "plc_module_ranks",
    "plc_rack_key",
    "plc_racks",
    "port_designation_key",
    "reading_ranks",
    "record_id_order",
    "series_part_key",
    "stub_far_key",
    "unit_designation_key",
    "units_in_order",
]


class _Placed(Protocol):
    """A record with a place on a page."""

    @property
    def x(self) -> int: ...

    @property
    def y(self) -> int: ...


def echo_entry_key(entry: tuple[int, int, int, str]) -> tuple[int, int, int, str]:
    """A tag echo's partner order: set rank, page, frame column, then text (layout-0089)."""
    return entry


def designation_key(model: Model, item: Id[Item]) -> NaturalKey:
    """`natural_key` of `item`'s printed designation: the one spelling of "by designation"."""
    return natural_key(item_designation(model, item))


def location_key(model: Model, node: Id[AspectNode]) -> tuple[NaturalKey, str]:
    """A `+` location's drawing-set order: its label in natural order, then the label (PAGE-02)."""
    label = aspect_nodes(model)[node].label
    return natural_key(label), label


def locations_in_order(model: Model, nodes: Iterable[Id[AspectNode]]) -> tuple[Id[AspectNode], ...]:
    """`nodes` in the order the drawing sets of a unit follow: by `location_key`, then by id."""
    return tuple(sorted(sorted(nodes), key=lambda node: location_key(model, node)))


def unit_designation_key(model: Model, unit: Id[Unit]) -> NaturalKey:
    """A unit's drawing-set order: its instance designation, naturally (`-U2` before `-U10`)."""
    return natural_key(instance_name(instance_tags(model, unit, None)))


def units_in_order(model: Model, units: Iterable[Id[Unit]]) -> tuple[Id[Unit], ...]:
    """`units` as their drawing sets follow the top level: by `unit_designation_key`, then id."""
    return tuple(sorted(sorted(units), key=lambda unit: unit_designation_key(model, unit)))


def port_designation_key(
    model: Model, port: Id[Port], *, unit: Id[Unit] | None = None
) -> NaturalKey:
    """`natural_key` of `port`'s printed designation: the one spelling of "ports by designation"."""
    return natural_key(port_designation(model, port, unit=unit))


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


type ChannelTie = tuple[int, NaturalKey, Id[Function]]
type ModuleKey = tuple[tuple[int, int], NaturalKey, tuple[str, ...]]


def plc_module_key(module: Item) -> ModuleKey:
    """Sort key of a PLC module in its rack: `position=`, else its own tag in natural order.

    The tag is the module's own designation without any block prefix, so renaming a function
    block never moves it (model-0259). The authoring key only breaks a tie.
    """
    return position_rank(module), natural_key(module.tag or ""), module.key


@digest_cached(DIGEST_CACHE_SIZE)
def plc_module_ranks(model: Model) -> frozendict[Id[Item], int]:
    """Each PLC module's place in the one order of modules: its rack, then `plc_module_key`.

    Ranks run from 0 over every module of every rack. The layout core iterates by them (R468).
    """
    known = items(model)
    modules = []
    for rack in sorted(plc_racks(model), key=lambda r: plc_rack_key(known[r])):
        found = [i for i in child_items(model, rack) if is_plc_module(model, known[i])]
        modules.extend(sorted(found, key=lambda i: plc_module_key(known[i])))
    return frozendict(zip(modules, range(len(modules)), strict=True))


def plc_rack_key(rack: Item) -> ModuleKey:
    """Sort key of a PLC rack: `position=`, else its own tag in natural order (model-0259).

    Like `plc_module_key`, it holds no block prefix, so renaming a block never reorders racks.
    """
    return position_rank(rack), natural_key(rack.tag or ""), rack.key


def plc_channel_tie(number: int, function: Function) -> ChannelTie:
    """Sort key of a channel within a module: its number, then the part's own function name.

    DI 1 and DO 1 share number 1; the template name (`di_1`, `do_1`) is the part's, so no id,
    which hashes the block tag, decides the tie. The id only breaks a repeat.
    """
    return number, natural_key(function.name), function.id


def plc_channel_key(
    model: Model, racks: frozenset[Id[Item]], item: Id[Item], number: int, function: Function
) -> tuple[int, ModuleKey | NaturalKey, int, ModuleKey, ChannelTie]:
    """Sort key of a PLC channel: the one order of the PLC list's tables and rows (model-0194).

    Racks by designation; in a rack its own channels, then each module by `plc_module_key`;
    channels by `plc_channel_tie`. Last come the channels on an item in no rack, by item
    designation. `racks` is `plc_racks(model)`.
    """
    record = items(model)[item]
    tail = plc_channel_tie(number, function)
    if item in racks:
        return (0, plc_rack_key(record), 0, ((0, 0), natural_key(""), ()), tail)
    if record.parent in racks and is_plc_module(model, record):
        return (0, plc_rack_key(items(model)[record.parent]), 1, plc_module_key(record), tail)
    return (1, designation_key(model, item), 0, ((0, 0), natural_key(""), ()), tail)


def by_place[T: _Placed](drawn: Iterable[T]) -> tuple[T, ...]:
    """`drawn` top-down, left to right; a tie keeps the order it came in.

    A page draws its symbols, labels and markers in this order, so no id (which follows the
    instance path) decides which is drawn first.
    """
    return tuple(sorted(drawn, key=lambda one: (one.y, one.x)))


def reading_ranks[K](points: Mapping[K, tuple[int, int]]) -> dict[K, int]:
    """Each key's reading order from 0 over its `(y, x)`: `by_place`'s order, a tie by arrival."""
    keys = sorted(points, key=lambda one: points[one])
    return {key: rank for rank, key in enumerate(keys)}


def record_id_order(ids: Iterable[str]) -> tuple[str, ...]:
    """Rendered record ids in the order the model's tables hold their records (`Id` order).

    The order of the record path, kept so the bytes of a drawing stay identical. The ids are of
    one kind, so the rendered `kind:value` text orders like the `Id`.
    """
    return tuple(sorted(ids))


def series_part_key(part: SeriesRowPart) -> NaturalKey:
    """A part of a parallel by its first symbol key, in natural order (SERIES-PARALLEL SP2)."""
    while not isinstance(part, str):
        part = part.parts[0]
    return natural_key(part)


def _local_designation(model: Model, record: object, unit: Id[Unit] | None) -> NaturalKey:
    """`natural_key` of the designation `record` prints in `unit`'s own document, else of `""`.

    A record names a `port`, a `function` or a `harness`; one that names none, or an item that
    prints none, keys as the empty text.
    """
    try:
        if (port := getattr(record, "port", None)) is not None:
            return port_designation_key(model, port, unit=unit)
        if (function := getattr(record, "function", None)) is not None:
            return natural_key(function_designation(model, function, unit=unit))
        if (harness := getattr(record, "harness", None)) is not None:
            return natural_key(item_designation(model, harness, unit=unit))
    except SchemaError:  # an item that prints no designation: the numbering finding names it
        pass
    return natural_key("")


def drawn_on_page[R: _Placed](model: Model, record_type: type[R], page: Page) -> tuple[R, ...]:
    """The page's `record_type` records in drawn order: top-down, left to right, then designation.

    A tie breaks on the designation as printed within the unit, then on the order it came in.
    """
    unit = layout_of(model, DrawingSet)[page.drawing_set].unit
    return tuple(
        sorted(
            page_slice(model, record_type, page),
            key=lambda one: (one.y, one.x, _local_designation(model, one, unit)),
        )
    )


def _printed(model: Model, subject: Id[Any]) -> str | None:
    """The subject's printed designation, or `None` for a kind that prints none or cannot."""
    try:
        if subject_kind(subject) is SubjectKind.ITEM:
            return item_designation(model, subject)
        if subject_kind(subject) is SubjectKind.PORT:
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


def findings_in_order(model: Model, findings: Iterable[Finding]) -> list[Finding]:
    """`findings` in print order: `finding_order_key`, then the message."""
    return sorted(findings, key=lambda f: (finding_order_key(model, f), f.message))


def stub_far_key(pick: tuple[Id[Port], Id[Port], Id[Conductor]]) -> tuple[str, str, str]:
    """A stub's far-end order of a `(near, far, conductor)`: far port, near port, conductor."""
    near, far, conductor = pick
    return far.value, near.value, conductor.value


def order_hint_key(hint: OrderHint) -> AuthoringKey:
    """An order hint's place in a list: its authoring key (model-0366)."""
    return hint.key
