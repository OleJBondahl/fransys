"""The BOM query: `bom_lines`, its unit scope and `TOP_LEVEL`.

See design/derive-queries.md, units spec U5.
"""

from typing import TYPE_CHECKING, Final, cast

from fransys_model.kernel import Id, Model, SchemaError
from fransys_model.vocab.membership import unit_own_roots
from fransys_model.vocab.tables import items, parts
from fransys_model.vocab.tables import units as units_table
lazy from fransys_model.vocab.aspects import AspectNode
lazy from fransys_model.vocab.core import Item, Unit

from .designation import (
    bom_sort_key,
    designation_holder,
    is_own_unit_root,
    location_designation,
    printed_designation,
    takes_parents_designation,
)
from .external import external
from .indexes import Indexes, build_indexes
from .instance_tag import instance_name, unit_tag
from .lookups import descendants, require
from .natural_order import natural_key
from .release_order import release_order
from .revision_text import revision_text
from .rows import BomLine
from .structure import items_at
from .unit_release import unit_release

if TYPE_CHECKING:
    from fransys_model.vocab.templates import Part

    from .release_order import ReleaseOrder


class TopLevelScope:
    """The type of `TOP_LEVEL`: a `bom_lines` scope distinct from `None` and every `Id[...]`."""

    __slots__ = ()


TOP_LEVEL: Final = TopLevelScope()
"""`bom_lines` scope: items with no unit, plus one line per top-level unit (units spec U5).

Distinct from `None`, which counts the whole model with no unit lines at all.
"""


def _in_scope(
    model: Model, idx: Indexes, scope: Id[Item] | Id[AspectNode] | None
) -> frozenset[Id[Item]] | None:
    """The items a BOM scope covers, or `None` for the whole model."""
    if scope is None:
        return None
    if scope.kind == "item":
        root = cast("Id[Item]", scope)
        require(items(model).get(root), "item", root)
        return frozenset({root, *descendants(idx.children_by_item, root)})
    if scope.kind == "aspect_node":
        return frozenset(items_at(model, cast("Id[AspectNode]", scope)))
    msg = "a BOM scope is an item or a location node of the model"
    raise SchemaError(msg, kind=scope.kind, record_id=scope)


def _unit_scope(
    model: Model, unit: Id[Unit] | None
) -> tuple[frozenset[Id[Item]], tuple[Unit, ...]]:
    """Items whose `unit` is exactly `unit`, and the `Unit`s whose `parent` is `unit`.

    `unit=None` is the top level: items with no unit, and top-level units.
    """
    covered = frozenset(item.id for item in items(model).values() if item.unit == unit)
    children = tuple(u for u in units_table(model).values() if u.parent == unit)
    return covered, children


def _instance_designations(model: Model, unit: Id[Unit]) -> list[str]:
    """One unit instance's BOM designations: a sole root's, else its locations, else its roots'.

    A location entry stands for the whole instance: roots without a location add nothing beside it.
    The roots are `vocab.membership.unit_own_roots`, external items left out.
    """
    if (tag := unit_tag(model, unit)) is not None:
        return [instance_name((tag,))]  # UT2: the instance is named by its tag
    roots = unit_own_roots(model, unit)
    if len(roots) == 1:
        return [printed_designation(model, roots[0])]
    locations = {loc for r in roots if (loc := location_designation(model, r)) is not None}
    if locations:
        return sorted(locations, key=natural_key)
    return [
        printed_designation(model, r) for r in sorted(roots, key=lambda i: bom_sort_key(model, i))
    ]


def _unit_lines(model: Model, children: tuple[Unit, ...]) -> list[tuple[ReleaseOrder, BomLine]]:
    """One `BomLine` per `(name, version, revision)` group of `children`, with its `release_order`.

    `mpn` is the unit's `number` (its `name` when empty), `description` its `title`.
    `count` is the number of instances, even when no designation is left.
    """
    grouped: dict[tuple[str, int, int], list[Unit]] = {}
    for child in children:
        release = unit_release(model, child.id)
        grouped.setdefault((release.name, release.version, release.revision), []).append(child)
    lines = []
    for (name, version, revision), instances in grouped.items():
        designations = [
            text for instance in instances for text in _instance_designations(model, instance.id)
        ]
        first = unit_release(model, instances[0].id)
        line = BomLine(
            part=None,
            mpn=first.number or name,
            manufacturer="",
            description=first.title,
            count=len(instances),
            designations=tuple(sorted(designations, key=natural_key)),
            revision=revision_text(version, revision),
        )
        lines.append((release_order(version, revision), line))
    return lines


def _bom_line_key(
    line: BomLine, order: ReleaseOrder
) -> tuple[str, ReleaseOrder, bool, Id[Part] | None]:
    """`(mpn, release order, part is None, part)`: total, and `None` is never compared to an `Id`.

    A part line has no release: its order is `(0, 0)`, below any release; revision is not sorted on.
    The third element is equal whenever the fourth is comparable, so `None < Id(...)` never occurs.
    """
    return (line.mpn, order, line.part is None, line.part)


def _part_designations(
    model: Model, ordered: list[Id[Item]], unit: Id[Unit] | None
) -> tuple[str, ...]:
    """`ordered`'s printed designations; a holder and its accessories give one text, in any order.

    The key is `designation_holder` (itself when no accessory); a key already printed is skipped.
    A holder that is `unit`'s own root prints nothing: its line stays, the cell omits it.
    """
    texts: list[str] = []
    printed: set[Id[Item]] = set()
    via_accessory: set[Id[Item]] = set()
    for item in ordered:
        key = designation_holder(model, item)
        if is_own_unit_root(model, key, unit):
            continue
        if takes_parents_designation(model, item):
            if key in printed:
                continue
            via_accessory.add(key)
        elif key in via_accessory:
            continue
        printed.add(key)
        texts.append(printed_designation(model, item, unit=unit))
    return tuple(texts)


def bom_lines(
    model: Model, scope: Id[Item] | Id[AspectNode] | Id[Unit] | TopLevelScope | None = None
) -> tuple[BomLine, ...]:
    """One `BomLine` per `Part` of an installed, not external item, by `(mpn, revision, part)`.

    An item with no `part` has no line. `designations` are `printed_designation`s; `revision` is
    `""` on a part line. A part with no installed item in scope has no line. `scope` narrows:

    - `None` (default): every installed item of the model, no unit lines.
    - `Id[Item]`: that item and its descendants; `Id[AspectNode]`: the items at or below it.
    - `Id[Unit]`: that unit's own items, plus one `part=None` line per unit instance nested in it.
      The unit's sole root keeps its line but prints no designation (`is_own_unit_root`).
    - `TOP_LEVEL`: items with no unit, plus one line per top-level unit, the same way.

    Raises:
        SchemaError: `scope` is none of the above kinds, names a unit the model does not hold,
            or a counted item has no designation.
    """
    idx = build_indexes(model)
    all_parts = parts(model)
    unit_children: tuple[Unit, ...] = ()
    own_unit = None  # L4 (R2): a unit's own BOM names its items as its own drawing does
    if isinstance(scope, TopLevelScope):
        covered, unit_children = _unit_scope(model, None)
    elif scope is not None and scope.kind == "unit":
        target = cast("Id[Unit]", scope)
        require(units_table(model).get(target), "unit", target)
        covered, unit_children = _unit_scope(model, target)
        own_unit = target
    else:
        covered = _in_scope(model, idx, cast("Id[Item] | Id[AspectNode] | None", scope))

    lines: list[tuple[ReleaseOrder, BomLine]] = []
    for part_id in idx.items_by_part:
        installed = [
            i
            for i in idx.items_by_part[part_id]
            if items(model)[i].installed
            and not external(model, i)
            and (covered is None or i in covered)
        ]
        if not installed:
            continue
        part = all_parts[part_id]
        ordered = sorted(installed, key=lambda i: bom_sort_key(model, i))
        part_line = BomLine(
            part=part_id,
            mpn=part.mpn,
            manufacturer=part.manufacturer,
            description=part.description,
            count=len(installed),
            designations=_part_designations(model, ordered, own_unit),
            revision="",
        )
        lines.append(((0, 0), part_line))
    lines.extend(_unit_lines(model, unit_children))
    keyed = sorted(
        ((_bom_line_key(line, order), line) for order, line in lines), key=lambda p: p[0]
    )
    return tuple(line for _, line in keyed)
