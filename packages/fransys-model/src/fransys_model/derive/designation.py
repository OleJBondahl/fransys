"""Designation rendering: the one place a human-readable label is built (design/derive-text.md).

Rendering only, and only ever in this direction. No function in this repo may ever parse
a designation back into an id or a `Placement` (CLAUDE.md red flag 1, design/foundations.md 2.2):
identity is always the `Id`, never the string a human reads. Adding a `parse_designation`
or similar is not a missing feature; it reintroduces the exact bug this model replaces
(design/examples.md 12: `"X1:3"`, `"DEV.CONN.PIN"` built and re-split).
"""

import contextlib
from itertools import islice
from typing import TYPE_CHECKING, Any
lazy from collections.abc import Iterable

from fransys_model.derive.accessory_blocks import is_contact_block, items_with_a_function_below
from fransys_model.derive.indexes import build_indexes
from fransys_model.derive.instance_tag import instance_designation, unit_root
from fransys_model.derive.lone_cable import printing_item
from fransys_model.derive.lookups import effective_placement, require, strip_set
from fransys_model.derive.natural_order import NaturalKey, natural_key
from fransys_model.derive.unit_nodes import SIGNS, chain_up, own_nodes_by_unit
from fransys_model.kernel import DIGEST_CACHE_SIZE, SchemaError, digest_cached, key_text
from fransys_model.vocab.enums import Aspect, FunctionKind
from fransys_model.vocab.facets.assigned_designation import AssignedDesignationFacet
from fransys_model.vocab.facets.connector import ConnectorFacet
from fransys_model.vocab.facets.pcb import FootprintFacet
from fransys_model.vocab.facets.terminal import TerminalFacet
from fransys_model.vocab.membership import (
    enclosing_boards,
    is_harness,
    is_sole_unit_root,
    item_chain,
    unit_own_roots,
    unit_subtree,
)
from fransys_model.vocab.own_designation import has_own_designation
from fransys_model.vocab.tables import (
    aspect_nodes,
    facets_of,
    functions,
    items,
    parts,
    placements,
    ports,
)
from fransys_model.vocab.tables import units as units_table
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.aspects import AspectNode
lazy from fransys_model.vocab.core import Function, Item, Port, Unit

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_model.vocab.templates import Part


def _facet_on[F](model: Model, subject: Id[Any], facet_type: type[F]) -> F | None:
    """The facet of `facet_type` on `subject`, read from the cached `facets_by_subject`."""
    facets = facets_of(model, facet_type)
    for facet in build_indexes(model).facets_by_subject.get(subject, ()):
        if facet in facets:
            return facets[facet]
    return None


def terminal_of(model: Model, item: Id[Item]) -> TerminalFacet | None:
    """`item`'s `terminal` facet, or `None` when it carries none."""
    return _facet_on(model, item, TerminalFacet)


def footprint_facet(model: Model, part: Id[Part]) -> FootprintFacet | None:
    """`part`'s `footprint` facet, or `None` when it carries none (a part has at most one)."""
    return _facet_on(model, part, FootprintFacet)


def own_designation_or_none(model: Model, item: Item) -> str | None:
    """`item`'s OWN text: its tag, else the assigned designation, else `None`; never raises.

    No holder arm, no terminal arm (both `_own_designation`'s); the one reader of the assigned text.
    `has_own_designation` holds the raw fact but returns no text, so this reads the facet itself.
    """
    if item.tag is not None:
        return item.tag
    if not has_own_designation(model, item):
        return None
    assigned = _facet_on(model, item.id, AssignedDesignationFacet)
    return None if assigned is None else assigned.text


def _own_designation(model: Model, item: Id[Item]) -> str:
    """`item`'s own label, with no enclosing board's designation in front (model-0040)."""
    record = items(model).get(item)
    if record is None:
        msg = "the id is not an item of the model"
        raise SchemaError(msg, kind="item", record_id=item)
    terminal = terminal_of(model, item)
    if terminal is not None:
        return f"{terminal.group}:{terminal.index}" if terminal.group else str(terminal.index)
    text = own_designation_or_none(model, record)
    if text is None:
        msg = "the item has no designation; run the numbering pass, which needs a part class code"
        raise SchemaError(msg, kind="item", record_id=item)
    return text


def item_label(model: Model, item: Item) -> str:
    """What an item is called in a message: its own text, else its authoring key joined by `/`.

    Reads no holder and no numbering, and never raises, so it serves an item that has no
    designation (`item_designation` raises).
    """
    text = own_designation_or_none(model, item)
    return text if text is not None else key_text(item)


@digest_cached(DIGEST_CACHE_SIZE)
def _items_with_a_function_at_or_below(model: Model) -> frozenset[Id[Item]]:
    """Every item with a function anywhere in its own subtree, itself included (model-0103 B10).

    Built once per `model.digest`: the items that carry a function, and (through
    `accessory_blocks.items_with_a_function_below`) every ancestor of one.
    """
    return items_with_a_function_below(model) | frozenset(build_indexes(model).functions_by_item)


def takes_parents_designation(model: Model, item: Id[Item]) -> bool:
    """Whether `item` is an accessory: it prints its parent's designation, having none of its own.

    True for a part-bearing item with no own text, terminal facet, board or harness role, whose
    `parent` is a designated part-bearing item (an own text, or a part class code), not a
    terminal, enclosing board or harness. A footprint part, or a function in the subtree (a
    device, but not an add-on contact block), makes `item` a part of its own. Unknown: `False`.

    Args:
        model: The frozen model to read.
        item: The item to classify.

    Returns:
        `True` if `item` is an accessory that prints its parent's designation.
    """
    all_items = items(model)
    record = all_items.get(item)
    if (
        record is None
        or record.part is None
        or own_designation_or_none(model, record) is not None
        or record.parent is None
        or terminal_of(model, item) is not None
        or item in enclosing_boards(model, item)  # includes `item` itself when it is a board
        or is_harness(model, item)
    ):
        return False
    if footprint_facet(model, record.part) is not None:
        return False
    if item in _items_with_a_function_at_or_below(model) and not is_contact_block(model, item):
        return False
    parent = all_items.get(record.parent)
    if (
        parent is None
        or (parent.part is None and parent.id not in strip_set(model))
        or terminal_of(model, parent.id) is not None
        or parent.id in enclosing_boards(model, item)
        or is_harness(model, parent.id)
    ):
        return False
    return own_designation_or_none(model, parent) is not None or bool(
        parent.part and parts(model)[parent.part].class_code
    )


def designation_holder(model: Model, item: Id[Item]) -> Id[Item]:
    """The item whose own label `item` prints: `item` itself, or the top of its accessory chain.

    Walks `parent` while `takes_parents_designation` holds; a parent cycle ends the walk.

    Args:
        model: The frozen model to read.
        item: The item whose label holder to find.

    Returns:
        `item` itself, or the topmost accessory ancestor whose label `item` prints.
    """
    holder = item
    for holder in item_chain(model, item):
        if not takes_parents_designation(model, holder):
            break
    return holder


def designating_ancestors(model: Model, item: Id[Item]) -> tuple[Id[Item], ...]:
    """Every enclosing board or harness of `item` by `Item.parent`, outermost first; never `item`.

    Cycle-safe: `enclosing_boards` for boards, `is_harness` for harnesses; never a rack or strip.
    An unknown `item` gives `()`, so `item_designation` raises via `_own_designation`, not here.
    """
    if items(model).get(item) is None:
        return ()
    boards = frozenset(enclosing_boards(model, item))
    above = islice(item_chain(model, item), 1, None)
    return tuple(reversed([node for node in above if node in boards or is_harness(model, node)]))


def _ancestor_label(model: Model, ancestor: Id[Item], *, is_board: bool) -> str:
    """An enclosing board's or harness's own label, or the refusal naming it.

    A harness refusal says to tag it (numbering gives it no class code); a board says run numbering.
    No terminal check: an ancestor in this chain is never a terminal.
    """
    record = items(model)[ancestor]
    if own_designation_or_none(model, record) is None:
        key = key_text(record)
        if is_board:
            msg = f"board {key} has no designation: run numbering; its part needs a class code"
        else:
            msg = f"harness {key} has no designation: give it a tag"
        raise SchemaError(msg, kind="item", record_id=ancestor)
    return _own_designation(model, ancestor)


def _render_item_designation(
    model: Model,
    item: Id[Item],
    *,
    relative_to: Id[Item] | None = None,
    unit: Id[Unit] | None = None,
) -> str:
    """Render `item`'s label: enclosing boards' and harnesses' labels dash-joined, outermost first.

    `relative_to` naming an enclosing board drops it and every ancestor outside it; else no effect.
    Raises the `SchemaError` `designation_refusal` returns; an accessory renders its holder's label.
    """
    if (
        refusal := designation_refusal(model, item, relative_to=relative_to, unit=unit)
    ) is not None:
        raise refusal
    if tagged := instance_designation(
        model, item, relative_to=relative_to, unit=unit, own=_render_item_designation
    ):
        return tagged  # UT2: the instance tags in front
    if unit is not None and relative_to is None:  # L4: printed in `unit`'s own document
        relative_to = unit_root(model, item, unit)
    ancestors = designating_ancestors(model, item := printing_item(model, item))  # model-0148
    # `enclosing_boards` does not tolerate an unknown item (unlike `designating_ancestors`);
    # skip it when there are no ancestors to classify, so an absent `item` still raises
    # through `_own_designation` below, not a `KeyError` here.
    boards = frozenset(enclosing_boards(model, item)) if ancestors else frozenset()
    if relative_to is not None and relative_to in ancestors and relative_to in boards:
        ancestors = ancestors[ancestors.index(relative_to) + 1 :]
    labels = [_ancestor_label(model, node, is_board=node in boards) for node in ancestors]
    labels.append(_own_designation(model, designation_holder(model, item)))
    return "-".join(labels)


@digest_cached(DIGEST_CACHE_SIZE)
def _plain_item_designations(model: Model) -> Mapping[Id[Item], str]:
    """Every item's plain-shape label (no `relative_to`, no `unit`), cached on `model.digest`.

    `item_designation` reads this map first for the plain shape; other calls take the live path.
    A raising item is left out: the miss falls through to `_render_item_designation`, which raises.
    """
    result: dict[Id[Item], str] = {}
    for item in items(model):
        with contextlib.suppress(SchemaError):
            result[item] = _render_item_designation(model, item)
    return result


def item_designation(
    model: Model,
    item: Id[Item],
    *,
    relative_to: Id[Item] | None = None,
    unit: Id[Unit] | None = None,
) -> str:
    """Render `item`'s label: a terminal's `group:index`, else its text, behind its chain (`A1-K1`).

    Args:
        model: The frozen model to read.
        item: The item to render.
        relative_to: An enclosing board: drops it and every ancestor outside it; `None` keeps all.
        unit: The unit whose own document is printed; drops its root's tag. `None`: whole model.

    Returns:
        `item`'s printed label; an accessory's is its holder's.

    Raises:
        SchemaError: `designation_refusal` of the same arguments is not `None`.
    """
    if relative_to is None and unit is None:
        cached = _plain_item_designations(model).get(item)
        if cached is not None:
            return cached
    return _render_item_designation(model, item, relative_to=relative_to, unit=unit)


def designation_refusal(
    model: Model,
    item: Id[Item],
    *,
    relative_to: Id[Item] | None = None,
    unit: Id[Unit] | None = None,
) -> SchemaError | None:
    """The `SchemaError` `item_designation(model, item, relative_to=, unit=)` raises, else `None`.

    The one home of "does `item` print": `item_designation` raises it; `can_print_designation` asks.
    Probes the chain via `_ancestor_label`, `_own_designation`, catching their raise; never raises.
    """
    if unit is not None and relative_to is None:
        relative_to = unit_root(model, item, unit)
    ancestors = designating_ancestors(model, item := printing_item(model, item))  # model-0148
    boards = frozenset(enclosing_boards(model, item)) if ancestors else frozenset()
    if relative_to is not None and relative_to in ancestors and relative_to in boards:
        ancestors = ancestors[ancestors.index(relative_to) + 1 :]
    try:
        for ancestor in ancestors:
            _ancestor_label(model, ancestor, is_board=ancestor in boards)
        _own_designation(model, designation_holder(model, item))
    except SchemaError as error:
        return error
    return None


def can_print_designation(model: Model, item: Id[Item]) -> bool:
    """Whether `item_designation(model, item)` renders rather than raises `SchemaError`.

    `designation_refusal(model, item) is None`, plain call: a `unit=` render refuses less.
    Lets a caller that must not raise ask first, never catch.
    """
    return designation_refusal(model, item) is None


def terminal_designation(model: Model, item: Id[Item], *, unit: Id[Unit] | None = None) -> str:
    """Render `item` as a terminal, connector pin or port named on its own (`-X1:L1:1`).

    Always a leading `-`; under a strip `-<strip label>:<group:index>`, parentless `-<own label>`.
    The one terminal text: `port_designation`, `printed_designation` and `terminal_rows` call it.
    """
    record = items(model).get(item)
    if record is None:
        msg = "the id is not an item of the model"
        raise SchemaError(msg, kind="item", record_id=item)
    if record.parent is not None and terminal_of(model, item) is not None:
        strip = item_designation(model, record.parent, unit=unit)
        return f"-{strip}:{_own_designation(model, item)}"
    return f"-{item_designation(model, item, unit=unit)}"


def connector_label(marking: str | None, name: str) -> str | None:
    """The label a connector function prints, `None` for none: the one home of that rule.

    `marking` is the `connector` facet's (or the part file's) `marking`, read like `Port.marking`:
    `None` means the function's own `name` is the label (`None` again for an empty name), and
    `""` means no label (a shell or an earth stud, whose pins print under the item). A function
    that is no connector has no label either: the caller does not ask. `_connector_label` here
    and the part lint call it after reading their own inputs.

    Args:
        marking: The connector facet's (or part file's) `marking`, or `None` for unset.
        name: The function's own name, the fallback label when `marking` is `None`.

    Returns:
        The label to print, or `None` for none.
    """
    if marking is None:
        return name or None
    return marking or None


def _connector_label(model: Model, function: Function) -> str:
    """The label `function` prints as a connector, `""` for none.

    A function that is no connector prints none; otherwise `connector_label` reads the facet's
    `marking` (`None` when there is no facet) and the function's name.
    """
    if function.kind is not FunctionKind.CONNECTOR:
        return ""
    facet = (
        None if function.template is None else _facet_on(model, function.template, ConnectorFacet)
    )
    return connector_label(None if facet is None else facet.marking, function.name) or ""


def prints_connector_label(model: Model, function: Id[Function]) -> bool:
    """Whether `function` is a connector that prints a label; `SchemaError` if it is not in `model`.

    False for a non-connector and for `marking=""` (a shell, an earth stud): it only adds its pins.
    `harness_cables` reads a housing end's connector facts from a function for which this is true.
    """
    record = functions(model).get(function)
    if record is None:
        msg = "the id is not a function of the model"
        raise SchemaError(msg, kind="function", record_id=function)
    return bool(_connector_label(model, record))


def connector_segments(labels: Iterable[str | None]) -> tuple[str, ...]:
    """The segment each function prints behind its item's designation, in order.

    `labels` holds the connector label of each function of one item: `""` or `None` for none
    (a function that is no connector, or a shell that says `marking=""`). A device prints its
    connectors as sub-parts (`-U2-X1:1`) when two or more of its functions have a label, so that
    two pins named alike never print one text: a labelled function then gives `-<label>`, an
    unlabelled one `""`. With no label, or one, every segment is `""` (`-J1:1`). This is the
    one place the rule is decided: `connector_segment` and the part lint both call it.

    Args:
        labels: Each function's connector label, in index order, `""` or `None` for none.

    Returns:
        Each function's printed segment, in the same order: `-<label>` or `""`.
    """
    given = tuple(labels)
    if sum(1 for label in given if label) <= 1:
        return ("",) * len(given)
    return tuple(f"-{label}" if label else "" for label in given)


def connector_segment(model: Model, function: Id[Function]) -> str:
    """`function`'s segment behind its item's designation (`-X1`), or `""`; raises if unknown.

    The label is the `connector` facet's `marking` when set, else the function's name.
    The one place the connector form is decided; `connector_segments` decides whether it prints.
    """
    all_functions = functions(model)
    record = all_functions.get(function)
    if record is None:
        msg = "the id is not a function of the model"
        raise SchemaError(msg, kind="function", record_id=function)
    siblings = build_indexes(model).functions_by_item.get(record.item, ())
    labels = [_connector_label(model, all_functions[sibling]) for sibling in siblings]
    return connector_segments(labels)[siblings.index(function)]


def connector_designation(
    model: Model, function: Id[Function], *, unit: Id[Unit] | None = None
) -> str:
    """Render the connector `function` as a list names it: `-J1`, or `-U2-X1` behind a device's tag.

    Decision model-0071. `printed_designation` of its item plus `connector_segment`. On the
    unit's own set a root item's connector drops the root's tag (`-X1`, as UNIT-ID I4 drops it
    for a child item): `is_own_unit_root` asks. A function that adds no segment prints its item
    as `printed_designation` does, root included.

    Raises:
        SchemaError: `function` is not a function of `model`, or its item has no designation.
    """
    segment = connector_segment(model, function)
    item = functions(model)[function].item
    if segment and is_own_unit_root(model, item, unit):
        return segment
    return printed_designation(model, item, unit=unit) + segment


def port_designation(model: Model, port: Id[Port], *, unit: Id[Unit] | None = None) -> str:
    """Render `port` as its item's designation and its name (`-K1:13`), always dash-prefixed.

    A terminal's port drops its name (`terminal_designation`); a connector pin reads `-U2-X1:1`.

    Args:
        model: The frozen model to read.
        port: The port to render.
        unit: The unit whose own document is printed; `None` renders the whole-model form.

    Returns:
        The port's printed label.

    Raises:
        SchemaError: `port` is not of `model`, or its item (a terminal's parent too) has none.
    """
    record = ports(model).get(port)
    if record is None:
        msg = "the id is not a port of the model"
        raise SchemaError(msg, kind="port", record_id=port)
    owner = items(model)[functions(model)[record.function].item]
    if terminal_of(model, owner.id) is None:
        return f"{connector_designation(model, record.function, unit=unit)}:{record.name}"
    return terminal_designation(model, owner.id, unit=unit)


def function_designation(
    model: Model, function: Id[Function], *, unit: Id[Unit] | None = None
) -> str:
    """Render `function` as its item's designation and its name (`JB1:J1`).

    Args:
        model: The frozen model to read.
        function: The function to render.
        unit: The unit whose own document is being printed; `None` renders the whole-model form.

    Returns:
        The function's printed label.

    Raises:
        SchemaError: `function` is not a function of `model`, or its item has no designation.
    """
    record = functions(model).get(function)
    if record is None:
        msg = "the id is not a function of the model"
        raise SchemaError(msg, kind="function", record_id=function)
    return f"{item_designation(model, record.item, unit=unit)}:{record.name}"


def _segment(
    nodes: frozendict[Id[AspectNode], AspectNode],
    leaf: AspectNode,
    sign: str,
    *,
    keep: frozenset[Id[AspectNode]] | None = None,
) -> str:
    """The labels from the root down to `leaf`, each behind `sign`; a parent cycle ends the walk.

    With `keep`, the label of a node outside it is left out (the walk still passes through).
    """
    labels = [
        f"{sign}{nodes[node].label}"
        for node in chain_up(nodes, leaf.id)
        if keep is None or node in keep
    ]
    return "".join(reversed(labels))


def own_nodes(model: Model, unit: Id[Unit]) -> frozenset[Id[AspectNode]]:
    """The aspect nodes that are `unit`'s own.

    Location node: every item at or below it is in `unit`'s subtree (cables and harnesses ignored).
    Function node: a unit item sits at or below it and no item of another unit does.

    Args:
        model: The frozen model to read.
        unit: The unit whose own nodes to find.

    Returns:
        The set of aspect node ids that are `unit`'s own.

    Raises:
        SchemaError: `unit` is not a unit of `model`.
    """
    require(units_table(model).get(unit), "unit", unit)
    return own_nodes_by_unit(model)[unit]


def is_own_unit_root(model: Model, item: Id[Item], unit: Id[Unit] | None) -> bool:
    """Whether `item` is the sole root of `unit`, the unit whose set is being listed.

    True when `item.unit == unit` and `item` is its sole root: a unit's own list omits that tag.

    Args:
        model: The frozen model to read.
        item: The item to test.
        unit: The unit whose set is being listed; `None` always answers `False`.

    Returns:
        `True` if `item` is the sole root of `unit`.

    Raises:
        SchemaError: `unit` is set and `item` is not an item of `model`.
    """
    return unit is not None and is_sole_unit_root(model, item) and items(model)[item].unit == unit


def _own_leaves(model: Model, item: Id[Item]) -> dict[Aspect, AspectNode]:
    """`item`'s own placements' nodes in the function and location aspects, one per aspect.

    An item placed twice in one aspect gives the placement with the smallest id.
    """
    nodes = aspect_nodes(model)
    all_placements = placements(model)
    leaves: dict[Aspect, AspectNode] = {}
    for placement in build_indexes(model).placements_by_item.get(item, ()):
        node = nodes[all_placements[placement].node]
        if node.aspect in SIGNS:
            leaves.setdefault(node.aspect, node)
    return leaves


def reference_leaves(model: Model, item: Id[Item]) -> dict[Aspect, AspectNode]:
    """The aspect -> leaf node `reference_designation` renders a segment from; unknown item: none.

    Own placements; a terminal lacking one takes its parent's (one hop, never further up).
    Not `effective_placement`, which inherits from any ancestor; numbering asks this too.
    """
    leaves = _own_leaves(model, item)
    record = items(model).get(item)
    if record is not None and record.parent is not None and terminal_of(model, item) is not None:
        for aspect, leaf in _own_leaves(model, record.parent).items():
            leaves.setdefault(aspect, leaf)
    return leaves


def reference_designation(model: Model, item: Id[Item], *, unit: Id[Unit] | None = None) -> str:
    """Render `item`'s full IEC 81346 reference: `=A1+C1-K1`, and `=A1-X1:L1:1` for a terminal.

    Own placements give the `=`/`+` labels (`reference_leaves`), then the product part, as printed.

    Args:
        model: The frozen model to read.
        item: The item to render.
        unit: The unit whose own document is printed: keeps its own nodes. `None`: whole model.

    Returns:
        `item`'s full IEC 81346 reference.

    Raises:
        SchemaError: as `item_designation`.
    """
    product = printed_designation(model, item, unit=unit)
    own = None if unit is None else own_nodes(model, unit)
    nodes = aspect_nodes(model)
    leaves = reference_leaves(model, item)
    segments = [
        _segment(nodes, leaves[aspect], sign, keep=own)
        for aspect, sign in SIGNS.items()
        if aspect in leaves
    ]
    return "".join(segments) + product


def printed_designation(model: Model, item: Id[Item], *, unit: Id[Unit] | None = None) -> str:
    """Render `item` as a list prints it: always behind its product-aspect sign (`-K1`, `-X1:L1:1`).

    A terminal with a parent: `terminal_designation`; any other item: `-` plus `item_designation`.

    Args:
        model: The frozen model to read.
        item: The item to render.
        unit: The unit whose own document is printed, for `item_designation`; `None`: whole model.

    Returns:
        `item`'s printed designation, dash-prefixed.

    Raises:
        SchemaError: as `item_designation`.
    """
    record = items(model).get(item)
    if record is not None and record.parent is not None and terminal_of(model, item) is not None:
        return terminal_designation(model, item, unit=unit)
    return f"-{item_designation(model, item, unit=unit)}"


def end_outside_nested_unit(model: Model, item: Id[Item], unit: Id[Unit] | None) -> bool:
    """Whether a list printed for `unit` leaves `item`'s end blank; raises if `unit` is unknown.

    True only for a nested `unit` whose subtree lacks `item`'s unit (an item in no unit is outside).
    A top-level `unit` and `unit=None` are never blank.
    """
    if unit is None:
        return False
    record = units_table(model).get(unit)
    if record is None:
        msg = "the id is not a unit of the model"
        raise SchemaError(msg, kind="unit", record_id=unit)
    if record.parent is None:
        return False
    return items(model)[item].unit not in unit_subtree(model, unit)


def unit_location(model: Model, unit: Id[Unit]) -> Id[AspectNode] | None:
    """The location node `unit` is placed at: its root items' location, else their common ancestor.

    The roots are `unit_own_roots` (external items left out), each
    read at its `effective_placement` in the location aspect. One
    location for all of them is that node; several are their nearest common ancestor in the
    location tree; `None` when no root is placed or the roots' locations share no ancestor.
    The context every list of a unit document prints its ends against.
    """
    nodes = aspect_nodes(model)
    paths: list[list[Id[AspectNode]]] = []
    for root in unit_own_roots(model, unit):
        leaf = effective_placement(model, root, Aspect.LOCATION)
        if leaf is not None:
            paths.append(list(reversed(list(chain_up(nodes, leaf)))))
    if not paths:
        return None
    common = paths[0]
    for path in paths[1:]:
        shared = 0
        for own, other in zip(common, path, strict=False):
            if own != other:
                break
            shared += 1
        common = common[:shared]
    return common[-1] if common else None


def unit_list_context(
    model: Model, unit: Id[Unit] | None, context: Id[AspectNode] | None
) -> Id[AspectNode] | None:
    """The location a list printed for `unit` prints its ends against.

    A unit's lists print against its own placement location (`unit_location`), not `context`;
    `context` stands only with no `unit` or no unit location; `unit=None` is `context` unchanged.
    """
    if unit is None:
        return context
    own = unit_location(model, unit)
    return context if own is None else own


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
        return (0, natural_key(item_designation(model, record.parent)), t.group, t.index)
    return (1, natural_key(item_designation(model, item)), "", 0)


def location_node_designation(model: Model, node: Id[AspectNode]) -> str:
    """Render a location node's signed path, root to leaf (`+C1`, nested `+ER+C1`).

    The `+` sign repeats at every level, exactly the segment `location_designation` renders
    for an item placed at `node`. Caution: not for a title block's scope cell, which
    deliberately keeps the bare label; only
    `location_designation` calls it there. `node` is not checked to be a location.
    """
    nodes = aspect_nodes(model)
    return _segment(nodes, nodes[node], SIGNS[Aspect.LOCATION])


def own_location_node(model: Model, item: Id[Item]) -> Id[AspectNode] | None:
    """The location node of `item`'s own `Aspect.LOCATION` placement, `None` when it has none.

    Own placement only, never an ancestor's; placed twice, the smallest id wins. Never raises.
    The one place this lookup lives: `location_designation` and `product_designation_in` use it.
    """
    nodes = aspect_nodes(model)
    all_placements = placements(model)
    leaf: AspectNode | None = None
    for placement in build_indexes(model).placements_by_item.get(item, ()):
        node = nodes[all_placements[placement].node]
        if node.aspect is Aspect.LOCATION and leaf is None:
            leaf = node
    return None if leaf is None else leaf.id


def location_designation(model: Model, item: Id[Item]) -> str | None:
    """Render `item`'s location segment (`+C1`, nested `+C1+SUB`), or `None` when it has none.

    The segment `product_designation` puts before the item's own label, from `own_location_node`.
    It never raises for an unknown or unnumbered item: such an item just has no segment.
    """
    leaf = own_location_node(model, item)
    if leaf is None:
        return None
    return location_node_designation(model, leaf)


def product_designation(model: Model, item: Id[Item]) -> str:
    """Render `item`'s printed physical tag: its location segment plus `-item_designation`.

    No `=` function segment, unlike `reference_designation`: this is the duplicate check's text.
    Raises as `item_designation`; an item with no location renders a bare `-{own}`.
    """
    own = item_designation(model, item)
    location = location_designation(model, item)
    if location is None:
        return f"-{own}"
    return f"{location}-{own}"
