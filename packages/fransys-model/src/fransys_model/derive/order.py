"""The one module of reader-order keys: natural designation order, bom lines, lists (model-0189).

Reached as `fransys_model.derive.order.<name>`; `derive/__init__.py` re-exports only the names
`derive.__all__` already held. A key over a printed designation needs the model, so it lives here,
above `vocab`; the text key itself is the kernel's `natural_key` (NUMBER-SORT K7).
"""

from typing import TYPE_CHECKING, Any, Protocol, cast

from fransys_model.derive.designation import (
    function_designation,
    item_designation,
    port_designation,
)
from fransys_model.derive.designation_label import terminal_of
from fransys_model.derive.facts.children import child_items
from fransys_model.derive.facts.item_predicates import is_plc_module
from fransys_model.derive.facts.roles import function_role, is_internal_port
from fransys_model.derive.facts.subjects import subject_kind
from fransys_model.derive.instance_tag import instance_name, instance_tags
from fransys_model.derive.lookups import position_rank
from fransys_model.derive.order_authoring import functions_by_authoring_key
from fransys_model.derive.placement_reads import has_function, port_function, port_name
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
from fransys_model.layout import DrawingSet, FrameCell, OrderHint, Page, layout_of, page_slice
from fransys_model.vocab.enums import SubjectKind
from fransys_model.vocab.tables import aspect_nodes, conductors, functions, items, ports
from fransys_model.vocab.tables import units as units_table
lazy from fransys_model.derive.rows_drawn import ConductorEnd, MateEnd
lazy from fransys_model.derive.rows_series_parallel import SeriesRowPart
lazy from fransys_model.vocab.aspects import AspectNode
lazy from fransys_model.vocab.connectivity import Conductor
lazy from fransys_model.vocab.core import Function, Item, Port, Unit

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from fransys_model.vocab.facets.terminal import TerminalFacet


__all__ = [
    "NaturalKey",
    "bom_sort_key",
    "cores_in_lane_order",
    "designation_key",
    "drawn_on_page",
    "finding_order_key",
    "findings_in_order",
    "function_order_text",
    "functions_by_authoring_key",
    "functions_in_order",
    "in_designation_order",
    "in_place_order",
    "location_key",
    "locations_in_order",
    "natural_key",
    "order_hint_key",
    "placement_key",
    "plc_channel_key",
    "plc_channel_tie",
    "plc_module_key",
    "plc_module_ranks",
    "plc_rack_key",
    "plc_racks",
    "port_designation_key",
    "reading_ranks",
    "series_part_key",
    "stub_far_order",
    "unit_designation_key",
    "units_in_order",
]


class _Placed(Protocol):
    """A record with a place on a page."""

    @property
    def x(self) -> int: ...

    @property
    def y(self) -> int: ...


def designation_key(model: Model, item: Id[Item]) -> NaturalKey:
    """`natural_key` of `item`'s printed designation: the one spelling of "by designation"."""
    return natural_key(item_designation(model, item))


def widest_text(texts: Iterable[str]) -> str:
    """The longest of `texts` (the first on a tie); "" when there are none."""
    return max(texts, key=len, default="")


def function_order_text(model: Model, function: Id[Function]) -> str:
    """A function's order as text: its item's printed designation, contacts after the rest, its name, its authoring key; never an Id."""
    record = functions(model)[function]
    contact = int(function_role(model, function).contact)
    return f"{item_designation(model, record.item)} {contact} {record.name} {'/'.join(record.key)}"


def _function_rank(model: Model, key: Id[Function] | Id[Port]) -> tuple[NaturalKey, NaturalKey, Id[Any]]:
    as_function = cast("Id[Function]", key)
    if has_function(model, as_function):
        return natural_key(function_order_text(model, as_function)), (), key
    port = cast("Id[Port]", key)
    return natural_key(function_order_text(model, cast("Id[Function]", port_function(model, port)))), natural_key(port_name(model, port)), key


def functions_in_order(model: Model, keys: Iterable[Id[Function] | Id[Port]]) -> tuple[Id[Function] | Id[Port], ...]:
    """Function keys (or a pin view's port) in `function_order_text` order, a port by its name; the Id ends a full tie."""
    return tuple(sorted(keys, key=lambda key: _function_rank(model, key)))


type _Block = tuple[Id[Unit] | None, Id[Item]]


def _block_key(model: Model, pair: _Block, *, cabled: bool) -> tuple[object, ...]:
    unit, subject = pair
    name = () if cabled else designation_key(model, subject)
    reading = (unit_designation_key(model, unit), units_table(model)[unit].key) if unit else ((), ())
    return (unit is not None, *reading, not cabled, name, items(model)[subject].key)


def blocks_in_print_order(model: Model, pairs: Iterable[_Block], *, cabled: set[_Block]) -> tuple[_Block, ...]:
    """Harness blocks in print order: absolute then units'; cable blocks by authoring key, then wire-only ones by designation."""
    return tuple(sorted(pairs, key=lambda pair: _block_key(model, pair, cabled=pair in cabled)))


def location_key(model: Model, node: Id[AspectNode]) -> tuple[NaturalKey, str]:
    """A `+` location's drawing-set order: its label in natural order, then the label (PAGE-02)."""
    label = aspect_nodes(model)[node].label
    return natural_key(label), label


def locations_in_order(model: Model, nodes: Iterable[Id[AspectNode]]) -> tuple[Id[AspectNode], ...]:
    """`nodes` in the order the drawing sets of a unit follow: by `location_key`, then the authoring key."""
    return tuple(sorted(nodes, key=lambda node: (location_key(model, node), aspect_nodes(model)[node].key)))


def unit_designation_key(model: Model, unit: Id[Unit]) -> NaturalKey:
    """A unit's drawing-set order: its instance designation, naturally (`-U2` before `-U10`)."""
    return natural_key(instance_name(instance_tags(model, unit, None)))


def units_in_order(model: Model, units: Iterable[Id[Unit]]) -> tuple[Id[Unit], ...]:
    """`units` as their drawing sets follow the top level: by `unit_designation_key`, then the authoring key."""
    return tuple(sorted(units, key=lambda unit: (unit_designation_key(model, unit), units_table(model)[unit].key)))


def port_designation_key(model: Model, port: Id[Port], *, unit: Id[Unit] | None = None) -> NaturalKey:
    """`natural_key` of `port`'s printed designation: the one spelling of "ports by designation"."""
    return natural_key(port_designation(model, port, unit=unit))


def first_terminal_port(model: Model, terminal_ports: Iterable[Id[Port]]) -> Id[Port]:
    """The port a terminal function's tag names: the internal side first, then the port name."""
    return min(terminal_ports, key=lambda port: (not is_internal_port(model, port), ports(model)[port].name))


def in_designation_order(model: Model, listed: Iterable[Id[Item]]) -> tuple[Id[Item], ...]:
    """`listed` sorted by `natural_key` of its designation (`-X2` before `-X10`), then the authoring key."""
    return tuple(sorted(listed, key=lambda item: (designation_key(model, item), items(model)[item].key)))


def terminals_in_order(model: Model, facets: Mapping[Id[Item], TerminalFacet]) -> tuple[Id[Item], ...]:
    """The terminals of `facets` in a strip's order: group in natural order, index, then authoring key."""
    return tuple(sorted(facets, key=lambda t: (natural_key(facets[t].group), facets[t].index, items(model)[t].key)))


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
    return frozenset(one.parent for one in items(model).values() if one.parent is not None and is_plc_module(model, one))


type ChannelTie = tuple[int, NaturalKey, AuthoringKey]
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
    which hashes the block tag, decides the tie. The function's authoring key only breaks a repeat.
    """
    return number, natural_key(function.name), function.key


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


def reading_ranks[K](points: Mapping[K, tuple[int, int]]) -> dict[K, int]:
    """Each key's reading rank from 0 over its `(y, x)`; a tie goes by arrival."""
    keys = sorted(points, key=lambda one: points[one])
    return {key: rank for rank, key in enumerate(keys)}


def in_place_order[T](found: Iterable[tuple[int, int, T]]) -> tuple[T, ...]:
    """The `(y, x, thing)` triples' things top-down, left to right; a tie keeps arrival order.

    The draw order of a page's elements: no id, which follows the instance path, decides it
    (NUMBER-SORT), so a rename leaves the bytes of a drawing unchanged.
    """
    return tuple(thing for _, _, thing in sorted(found, key=lambda one: one[:2]))


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


def placement_key(model: Model, page: Id[Page], cell: FrameCell) -> tuple[int, int, int, str]:
    """A placement's place in a list: its drawing set, its page number, then its frame cell (column, row) (R1571)."""
    placed = layout_of(model, Page)[page]
    return layout_of(model, DrawingSet)[placed.drawing_set].number, placed.number, cell.column, cell.row


def stub_far_order(model: Model, ends: Iterable[ConductorEnd | MateEnd]) -> list[ConductorEnd | MateEnd]:
    """A stub's ends in print order: a conductor end before a mate end (S3), the far and near ports' printed designations, then the key (R1581).

    The first end is the one a pin names its line and carrier by: `cut_lines` and `far_port` read it.
    """
    return sorted(
        ends, key=lambda e: (isinstance(e, MateEnd), port_designation_key(model, e.far), port_designation_key(model, e.port), _end_key(model, e))
    )


def _end_key(model: Model, end: ConductorEnd | MateEnd) -> tuple[str, ...]:
    """A conductor end's own key, a mate end's mate id."""
    return (end.mate.value,) if isinstance(end, MateEnd) else conductors(model)[end.conductor].key


def cores_in_lane_order(index: Mapping[Id[Conductor], int], conductors: Iterable[Id[Conductor]]) -> list[Id[Conductor]]:
    """A line's conductors by core index (a wire past the cores has none and goes first), then id."""
    return sorted(conductors, key=lambda c: (index.get(c, 0), c.value))


def order_hint_key(hint: OrderHint) -> AuthoringKey:
    """An order hint's place in a list: its authoring key (model-0366)."""
    return hint.key
