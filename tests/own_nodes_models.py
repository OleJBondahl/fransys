"""The models `test_own_nodes.py` checks `own_nodes` on: builders only, no expected values.

Most builders return a frozen `Model` of two cabinet instances under one container unit (the
scale fixture's shape, `n=2`), with one change that makes a part of the `own_nodes` rule matter.
The last three are hand-built small models for the corners the authoring API cannot make.
"""

import dataclasses
import sys
from decimal import Decimal
from pathlib import Path

import fransys as fr
import fransys_author
import fransys_parts

from fransys_model.derive.designation import own_designation_or_none
from fransys_model.kernel import Draft, Origin, evolve, freeze, make_id
from fransys_model.vocab import (
    Aspect,
    AspectNode,
    CableFacet,
    CableProductFacet,
    Item,
    Part,
    PartCategory,
    Placement,
    Unit,
    UnitRelease,
)
from fransys_model.vocab.tables import aspect_nodes, items, placements

_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    # `--import-mode=importlib` (root pyproject.toml) never puts this folder on `sys.path`.
    sys.path.insert(0, str(_TESTS_DIR))

from scale_units_fixture import PROJECT, build_scale, pump_cabinet  # noqa: E402

N = 2


def scale_model():
    """The scale fixture, unchanged."""
    return build_scale(N).model


def _build_with(extra):
    """The scale design (the fixture's steps), then `extra(d, container, er)` before the build."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**PROJECT)
    d.revision(1, date="2026-09-25", text="First issue", created="XX")
    er = d.location("ER", "Engine room")
    container = d.unit("scale-container", revision=1, interface="1")
    container.revision(1, date="2026-01-01", text="First release", created="XX")
    for i in range(1, N + 1):
        field = pump_cabinet(container.scope(f"pump{i}", at=er), name=f"C{i}")
        for terminal in field:
            container.unused(terminal)
    extra(d, container, er)
    return fr.build(parts, d.draft()).model


def _fld_group(d):
    """The `=FLD` group of `pump1`'s cabinet unit, declared again with its own key (same record)."""
    return d.scope("pump1").group("FLD", "Field wiring")


def item_in_no_unit_at_er():
    """A top-level item, in no unit, placed at `+ER`."""

    def extra(d, _container, er):
        d.item("DEMO-CONN-2P", tag="S1", at=er, group=d.group("TOP", "Top level"))

    return _build_with(extra)


def item_in_no_unit_in_fld():
    """A top-level item, in no unit, placed in `pump1`'s `=FLD` group (F9)."""

    def extra(d, _container, _er):
        d.item("DEMO-CONN-2P", tag="S1", group=_fld_group(d))

    return _build_with(extra)


def item_of_another_unit_in_fld():
    """An item of the container unit placed in `pump1`'s `=FLD` group (F9)."""

    def extra(d, container, _er):
        container.scope("stray").item("DEMO-CONN-2P", tag="S1", group=_fld_group(d))

    return _build_with(extra)


def _location_node(model, label):
    (found,) = (
        n.id
        for n in aspect_nodes(model).values()
        if n.aspect is Aspect.LOCATION and n.label == label
    )
    return found


def x2_placed_twice(*, second_wins):
    """`pump1`'s `X2` strip also placed at `+C2`, where `pump2`'s items are.

    A second placement in one aspect counts only when its id sorts first
    (`effective_placement` takes the smallest); `second_wins` picks a key whose id sorts before
    (True) or after (False) the strip's own location placement.
    """
    model = scale_model()
    nodes = aspect_nodes(model)
    (strip,) = (
        i
        for i in items(model).values()
        if i.key[0] == "pump1" and own_designation_or_none(model, i) == "X2"
    )
    own = min(
        p.id
        for p in placements(model).values()
        if p.item == strip.id and nodes[p.node].aspect is Aspect.LOCATION
    )
    c2 = _location_node(model, "C2")
    for attempt in range(1000):
        key = (*strip.key, "again", str(attempt))
        pid = make_id(Placement, key)
        if (pid < own) is second_wins:
            record = Placement(id=pid, key=key, item=strip.id, node=c2)
            return evolve(model, put=[record], origin=Origin(file="<twice>", line=1, note="2b"))
    msg = "no key found"
    raise AssertionError(msg)


# -- hand-built models: keys under one scope, records with as little content as they need --

_SCOPE = "own"


def _release(name):
    key = ("unit_release", name, "1", "1")
    return UnitRelease(
        id=make_id(UnitRelease, key), key=key, name=name, version=1, revision=1, interface="1"
    )


def _unit(name, parent=None):
    key = (_SCOPE, "unit", name)
    return Unit(
        id=make_id(Unit, key),
        key=key,
        release=_release(name).id,
        parent=None if parent is None else parent.id,
    )


def _node(aspect, label, parent=None):
    key = (_SCOPE, "node", label)
    return AspectNode(
        id=make_id(AspectNode, key),
        key=key,
        aspect=aspect,
        parent=None if parent is None else parent.id,
        label=label,
        description=label,
    )


def _item(name, *, unit=None, parent=None, part=None):
    key = (_SCOPE, "item", name)
    return Item(
        id=make_id(Item, key),
        key=key,
        part=part,
        parent=None if parent is None else parent.id,
        position=None,
        tag=None,
        description=name,
        unit=None if unit is None else unit.id,
        external=False,
    )


def _at(item, node):
    key = (*item.key, "at", node.label)
    return Placement(id=make_id(Placement, key), key=key, item=item.id, node=node.id)


def _cable_facet(item):
    key = (*item.key, "facet")
    return CableFacet(id=make_id(CableFacet, key), key=key, subject=item.id, length_mm=None)


def _cable_part(name):
    """A cable-product `Part` (RW4b, model-0108): the fact that makes an item a cable.

    No `Conductor` of kind `core` names this fixture's cable items as carrier, so
    `core_colours=()` is correct here.
    """
    key = (_SCOPE, "part", name)
    part = Part(
        id=make_id(Part, key),
        key=key,
        mpn=f"EXAMPLE-{name}",
        manufacturer="Example Co",
        description=name,
        category=PartCategory.CABLE,
        class_code="W",
    )
    product_key = (*key, "product")
    product = CableProductFacet(
        id=make_id(CableProductFacet, product_key),
        key=product_key,
        subject=part.id,
        core_colours=(),
        gauge_mm2=Decimal("1.5"),
        shielded=False,
    )
    return part, product


def _freeze(records):
    draft = Draft()
    releases = {r.key[2]: _release(r.key[2]) for r in records if isinstance(r, Unit)}
    draft.extend(
        (*releases.values(), *records),
        origin=Origin(file="<own_nodes model>", line=1, note="model-0067"),
    )
    return freeze(draft)


def cross_aspect_nodes():
    """Unit `a`'s item at `+C1`, whose parent is the function node `=P1`; unit `b`'s item at `=P1`.

    An `ASPECT_CROSS_PARENT` model that `freeze` still accepts: `+C1`'s chain up reaches `=P1`
    through `parent`, so `=P1` is reached in both aspects.
    """
    unit_a, unit_b = _unit("a"), _unit("b")
    p1 = _node(Aspect.FUNCTION, "P1")
    c1 = _node(Aspect.LOCATION, "C1", p1)
    item_a, item_b = _item("item-a", unit=unit_a), _item("item-b", unit=unit_b)
    return _freeze((unit_a, unit_b, p1, c1, item_a, item_b, _at(item_a, c1), _at(item_b, p1)))


def cable_ends_in_a_unit_location():
    """Unit `u` has items at `+C1`, `+C2` and `+C3`; things in no unit are placed at them too.

    At `+C1` a top-level cable, at `+C2` the plug of a top-level harness (the harness holds a
    cable child), at `+C3` an ordinary item that is a cable's or harness's neither.
    """
    unit = _unit("u")
    c1, c2, c3 = (_node(Aspect.LOCATION, name) for name in ("C1", "C2", "C3"))
    inside = [_item(f"in-{n}", unit=unit) for n in (1, 2, 3)]
    cable_part, cable_product = _cable_part("cable")
    harness_cable_part, harness_cable_product = _cable_part("harness-cable")
    cable = _item("cable", part=cable_part.id)
    harness = _item("harness")
    harness_cable = _item("harness-cable", parent=harness, part=harness_cable_part.id)
    plug = _item("plug", parent=harness)
    loose = _item("loose")
    return _freeze(
        (
            unit,
            c1,
            c2,
            c3,
            *inside,
            cable_part,
            cable_product,
            harness_cable_part,
            harness_cable_product,
            cable,
            harness,
            harness_cable,
            plug,
            loose,
            _cable_facet(cable),
            _cable_facet(harness_cable),
            *(_at(item, node) for item, node in zip(inside, (c1, c2, c3), strict=True)),
            _at(cable, c1),
            _at(plug, c2),
            _at(loose, c3),
        )
    )


def units_naming_each_other_as_parent():
    """Units `x` and `y` are each other's `parent`; each has an item at its own location.

    `x`'s item is also in the group `=G`. `+Z` holds an item in no unit.
    """
    unit_x, unit_y = _unit("x"), _unit("y")
    unit_x = dataclasses.replace(unit_x, parent=unit_y.id)
    unit_y = dataclasses.replace(unit_y, parent=unit_x.id)
    cx, cy, cz = (_node(Aspect.LOCATION, name) for name in ("CX", "CY", "CZ"))
    group = _node(Aspect.FUNCTION, "G")
    item_x, item_y = _item("item-x", unit=unit_x), _item("item-y", unit=unit_y)
    loose = _item("loose")
    return _freeze(
        (
            unit_x,
            unit_y,
            cx,
            cy,
            cz,
            group,
            item_x,
            item_y,
            loose,
            _at(item_x, cx),
            _at(item_x, group),
            _at(item_y, cy),
            _at(loose, cz),
        )
    )
