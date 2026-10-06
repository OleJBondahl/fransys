"""PLC-SCOPE tests: a request is served by the first unit on its chain that declares its signal.

The chain is the request's own unit, its `Unit.parent`s, and the top level (`Item.unit` None)
last. One free-channel queue per (unit, signal type), the order inside each queue unchanged; an
exhausted serving unit gets `PLC_REQUEST_UNSERVABLE` with no fall-through (designer ruling
2026-09-25). Invented data: unit B's rack key sorts before unit A's, so a model-wide queue
would hand unit A the channels of unit B.
"""

import dataclasses
from typing import TYPE_CHECKING

from plant import Plant

from fransys_model.derive import plc_channel_rows
from fransys_model.derive.passes.plc_allocation import PLC_REQUEST_UNSERVABLE, allocate_plc
from fransys_model.kernel import Model, make_id
from fransys_model.vocab.core import Unit
from fransys_model.vocab.enums import FunctionKind, PartCategory, SignalType
from fransys_model.vocab.facets.plc import PlcBindingFacet, PlcChannelFacet, PlcRequestFacet
from fransys_model.vocab.tables import facets_of, functions
from fransys_model.vocab.templates import FunctionTemplate, Part
from fransys_model.vocab.validators.plc import check_plc, check_plc_wiring

if TYPE_CHECKING:
    from fransys_model.kernel import Id
    from fransys_model.vocab.core import Function


@dataclasses.dataclass(frozen=True)
class Site:
    """A PLC rack item holding one module of free DI channels, in `unit` (None: top level)."""

    rack: str
    module: str
    module_designation: str
    channels: int
    unit: Id[Unit] | None = None


def _site(plant: Plant, site: Site) -> list[Id[Function]]:
    """Add the rack item and, under it, the module with its channel functions."""
    rack = plant.item(site.rack, designation=f"R-{site.rack}", unit=site.unit)
    part = Part(
        id=make_id(Part, (site.module, "part")),
        key=(site.module, "part"),
        mpn=f"EXAMPLE-{site.module}",
        manufacturer="Example Co",
        description="Invented",
        category=PartCategory.PLC_MODULE,
        class_code="A",
    )
    plant.add(part)
    module = plant.item(
        site.module,
        designation=site.module_designation,
        part=part.id,
        parent=rack,
        unit=site.unit,
    )
    found = []
    for number in range(1, site.channels + 1):
        template = FunctionTemplate(
            id=make_id(FunctionTemplate, (site.module, "part", f"ch{number}")),
            key=(site.module, "part", f"ch{number}"),
            part=part.id,
            name=f"ch{number}",
            kind=FunctionKind.PLC_CHANNEL,
        )
        facet = PlcChannelFacet(
            id=make_id(PlcChannelFacet, (site.module, str(number), "facet")),
            key=(site.module, str(number), "facet"),
            subject=template.id,
            signal=SignalType.DI,
            channel=number,
        )
        plant.add(template, facet)
        found.append(plant.function(module, f"ch{number}", template=template.id))
    return found


def _device(
    plant: Plant,
    name: str,
    unit: Id[Unit] | None,
    *,
    priority: int = 1,
    channel: Id[Function] | None = None,
) -> Id[Function]:
    """A field device with a DI request; wired to `channel`'s pin 1 when `channel` is given."""
    item = plant.item(name, designation=f"B-{name}", unit=unit)
    function = plant.function(item, "signal")
    plant.add(
        PlcRequestFacet(
            id=make_id(PlcRequestFacet, (name, "signal", "request")),
            key=(name, "signal", "request"),
            subject=function,
            signal=SignalType.DI,
            signal_name=f"tag_{name}",
            priority=priority,
        )
    )
    if channel is not None:
        plant.wire(plant.port(function, "1"), plant.port(channel, "1"), key=f"wire-{name}")
    return function


@dataclasses.dataclass(frozen=True)
class Built:
    """A frozen model with unit A's devices, its channels and the unit (None when built alone)."""

    model: Model
    unit_a: Id[Unit] | None
    devices: list[Id[Function]]
    channels: list[Id[Function]]


def _units_a_and_b(*, alone: bool = False) -> Built:
    """Unit A: rack `rack-b2`, 3 wired devices; unit B: rack `rack-a1` (sorts first), 3 channels.

    `alone` builds the same A records with `unit=None` and no B, no unit records.
    """
    plant = Plant()
    unit_a = None if alone else plant.unit("unit-a", name="unit A")
    channels = _site(plant, Site("rack-b2", "mod-a", "A1", 3, unit_a))
    if not alone:
        unit_b = plant.unit("unit-b", name="unit B")
        _site(plant, Site("rack-a1", "mod-b", "A2", 3, unit_b))
    devices = [
        _device(plant, f"dev-a{number}", unit_a, channel=channel)
        for number, channel in enumerate(channels, start=1)
    ]
    return Built(plant.model(), unit_a, devices, channels)


def _bound(model: Model) -> dict[Id[Function], Id[Function]]:
    return {b.subject: b.channel for b in facets_of(model, PlcBindingFacet).values()}


def _binding_keys(model: Model) -> dict[tuple[str, ...], tuple[str, ...]]:
    """`{request function key: channel function key}`."""
    all_functions = functions(model)
    return {all_functions[r].key: all_functions[c].key for r, c in _bound(model).items()}


def test_a_units_requests_bind_to_its_own_racks_channels_and_match_the_wiring() -> None:
    """Unit B's rack sorts first, yet A's requests take A's channels and nothing mismatches."""
    built = _units_a_and_b()
    model, findings = allocate_plc(built.model)
    assert findings == ()
    assert check_plc_wiring(model) == ()
    assert _bound(model) == dict(zip(built.devices, built.channels, strict=True))


def test_a_unit_built_alone_and_inside_a_system_get_the_same_bindings() -> None:
    """The unit's PLC list and its `{request: channel}` keys equal the stand-alone ones."""
    alone, alone_findings = allocate_plc(_units_a_and_b(alone=True).model)
    system_built = _units_a_and_b()
    system, system_findings = allocate_plc(system_built.model)
    assert alone_findings == system_findings == ()
    columns = ("channel_designation", "signal", "wired_to", "field_device_designation")
    columns += ("signal_name",)
    alone_rows = [
        tuple(getattr(row, column) for column in columns) for row in plc_channel_rows(alone)
    ]
    system_rows = [
        tuple(getattr(row, column) for column in columns)
        for row in plc_channel_rows(system, unit=system_built.unit_a)
    ]
    assert len(alone_rows) == 3
    assert system_rows == alone_rows
    assert _binding_keys(system) == _binding_keys(alone)


def test_a_unit_short_of_its_own_channels_is_unservable_however_free_another_unit_is() -> None:
    """Three requests, two channels in A, five free in B: the third request gets the ERROR."""
    plant = Plant()
    unit_a = plant.unit("unit-a", name="unit A")
    unit_b = plant.unit("unit-b", name="unit B")
    own = _site(plant, Site("rack-b2", "mod-a", "A1", 2, unit_a))
    _site(plant, Site("rack-a1", "mod-b", "A2", 5, unit_b))
    devices = [_device(plant, f"dev-a{number}", unit_a) for number in (1, 2, 3)]
    model, (finding,) = allocate_plc(plant.model())
    assert _bound(model) == dict(zip(devices[:2], own, strict=True))
    assert finding.code == PLC_REQUEST_UNSERVABLE
    assert devices[2] in finding.subjects
    assert "dev-a3/signal" in finding.message
    assert devices[2] not in _bound(model)


def test_a_top_level_request_binds_only_to_a_top_level_rack() -> None:
    """The unit rack `rack-a1` sorts first, but the top-level request takes `rack-t9`'s channel."""
    plant = Plant()
    unit_a = plant.unit("unit-a", name="unit A")
    _site(plant, Site("rack-a1", "mod-u", "A1", 1, unit_a))
    (top_channel,) = _site(plant, Site("rack-t9", "mod-t", "A9", 1))
    top = _device(plant, "dev-top", None)
    model, findings = allocate_plc(plant.model())
    assert findings == ()
    assert _bound(model) == {top: top_channel}


def test_a_top_level_request_with_only_a_unit_rack_declared_is_unservable() -> None:
    """A unit's channels are not the top level's: one ERROR, no binding."""
    plant = Plant()
    unit_a = plant.unit("unit-a", name="unit A")
    _site(plant, Site("rack-a1", "mod-u", "A1", 1, unit_a))
    top = _device(plant, "dev-top", None)
    model, (finding,) = allocate_plc(plant.model())
    assert _bound(model) == {}
    assert finding.code == PLC_REQUEST_UNSERVABLE
    assert top in finding.subjects


def test_units_each_with_exactly_enough_channels_are_all_served_in_priority_then_key_order() -> (
    None
):
    """Guard: inside a unit the priority ranks before the key, as before the unit scope."""
    plant = Plant()
    unit_a = plant.unit("unit-a", name="unit A")
    unit_b = plant.unit("unit-b", name="unit B")
    a_channels = _site(plant, Site("rack-b2", "mod-a", "A1", 2, unit_a))
    b_channels = _site(plant, Site("rack-a1", "mod-b", "A2", 2, unit_b))
    x1 = _device(plant, "dev-x1", unit_b, priority=2)
    x2 = _device(plant, "dev-x2", unit_b, priority=1)
    y1 = _device(plant, "dev-y1", unit_a, priority=4)
    y2 = _device(plant, "dev-y2", unit_a, priority=3)
    model, findings = allocate_plc(plant.model())
    assert findings == ()
    assert _bound(model) == {
        x2: b_channels[0],
        x1: b_channels[1],
        y2: a_channels[0],
        y1: a_channels[1],
    }
    assert check_plc(model) == ()


def test_a_nested_unit_that_declares_no_channel_takes_its_parents_channel() -> None:
    """The child has no DI channel of its own: its request binds on the parent's rack."""
    plant = Plant()
    parent = plant.unit("parent", name="parent")
    child = plant.unit("child", name="child", parent=parent)
    channels = _site(plant, Site("rack-p", "mod-p", "P1", 2, parent))
    device = _device(plant, "dev-c", child, channel=channels[0])
    model, findings = allocate_plc(plant.model())
    assert findings == ()
    assert check_plc_wiring(model) == ()
    assert _bound(model) == {device: channels[0]}


def test_a_nested_unit_short_of_its_own_channels_is_unservable_though_its_parent_has_free() -> None:
    """The child declares one DI channel: request 1 takes it, request 2 falls no further."""
    plant = Plant()
    parent = plant.unit("parent", name="parent")
    child = plant.unit("child", name="child", parent=parent)
    parent_channels = _site(plant, Site("rack-a1", "mod-p", "P1", 3, parent))
    (own,) = _site(plant, Site("rack-c1", "mod-c", "C1", 1, child))
    first = _device(plant, "dev-c1", child)
    second = _device(plant, "dev-c2", child)
    model, (finding,) = allocate_plc(plant.model())
    assert _bound(model) == {first: own}
    assert not set(parent_channels) & set(_bound(model).values())
    assert finding.code == PLC_REQUEST_UNSERVABLE
    assert second in finding.subjects
    assert "is taken" in finding.message


def test_a_parents_request_never_binds_to_a_nested_units_rack() -> None:
    """Only the child holds a rack: nothing reaches downward, the parent's request is unservable."""
    plant = Plant()
    parent = plant.unit("parent", name="parent")
    child = plant.unit("child", name="child", parent=parent)
    _site(plant, Site("rack-c1", "mod-c", "C1", 2, child))
    device = _device(plant, "dev-p", parent)
    model, (finding,) = allocate_plc(plant.model())
    assert _bound(model) == {}
    assert finding.code == PLC_REQUEST_UNSERVABLE
    assert device in finding.subjects
    assert "declares no" in finding.message


def _siblings(*, parent_declares: bool) -> tuple[Model, Id[Function], list[Id[Function]]]:
    """Child x holds a rack, child y has the request; also the parent's channels (if declared)."""
    plant = Plant()
    parent = plant.unit("parent", name="parent")
    unit_x = plant.unit("unit-x", name="unit X", parent=parent)
    unit_y = plant.unit("unit-y", name="unit Y", parent=parent)
    _site(plant, Site("rack-a1", "mod-x", "X1", 2, unit_x))
    parent_channels = (
        _site(plant, Site("rack-p1", "mod-p", "P1", 1, parent)) if parent_declares else []
    )
    device = _device(plant, "dev-y", unit_y)
    return plant.model(), device, parent_channels


def test_a_sibling_never_shares_a_rack_so_a_child_with_no_declaring_ancestor_is_unservable() -> (
    None
):
    """Unit X's rack is not unit Y's, and the parent declares nothing: one ERROR."""
    model, _, _ = _siblings(parent_declares=False)
    bound, (finding,) = allocate_plc(model)
    assert _bound(bound) == {}
    assert finding.code == PLC_REQUEST_UNSERVABLE
    assert "declares no" in finding.message


def test_a_sibling_child_is_served_by_the_parent_when_the_parent_declares() -> None:
    """Y takes the parent's channel and never sibling X's rack (which sorts first)."""
    model, device, parent_channels = _siblings(parent_declares=True)
    bound, findings = allocate_plc(model)
    assert findings == ()
    assert _bound(bound) == {device: parent_channels[0]}


def test_a_top_level_unit_that_declares_no_channel_takes_a_top_level_rack() -> None:
    """The unit has no parent; the top level (`Item.unit` None) is the last link of its chain."""
    plant = Plant()
    unit = plant.unit("unit-u", name="unit U")
    (top_channel,) = _site(plant, Site("rack-t9", "mod-t", "T1", 1))
    device = _device(plant, "dev-u", unit, channel=top_channel)
    model, findings = allocate_plc(plant.model())
    assert findings == ()
    assert check_plc_wiring(model) == ()
    assert _bound(model) == {device: top_channel}


def test_a_grandchild_uses_the_grandparents_channel_when_neither_it_nor_its_parent_declares() -> (
    None
):
    """The chain is walked past the parent to the grandparent."""
    plant = Plant()
    grandparent = plant.unit("grandparent", name="grandparent")
    parent = plant.unit("parent", name="parent", parent=grandparent)
    grandchild = plant.unit("grandchild", name="grandchild", parent=parent)
    (channel,) = _site(plant, Site("rack-g1", "mod-g", "G1", 1, grandparent))
    device = _device(plant, "dev-g", grandchild, channel=channel)
    model, findings = allocate_plc(plant.model())
    assert findings == ()
    assert check_plc_wiring(model) == ()
    assert _bound(model) == {device: channel}


def test_a_unit_parent_loop_does_not_hang_the_allocation() -> None:
    """Units a and b are each other's parent (`freeze` accepts it, `UNIT_CYCLE` comes later)."""
    a_id, b_id = make_id(Unit, ("a",)), make_id(Unit, ("b",))
    plant = Plant()
    release = plant.release("u")
    plant.add(
        Unit(id=a_id, key=("a",), release=release, parent=b_id),
        Unit(id=b_id, key=("b",), release=release, parent=a_id),
    )
    device = _device(plant, "dev-a", a_id)
    model, (finding,) = allocate_plc(plant.model())
    assert _bound(model) == {}
    assert finding.code == PLC_REQUEST_UNSERVABLE
    assert device in finding.subjects


def test_the_nearest_declaring_ancestor_serves_not_the_outermost() -> None:
    """The parent and the grandparent both declare DI; the grandparent's rack sorts first."""
    plant = Plant()
    grandparent = plant.unit("grandparent", name="grandparent")
    parent = plant.unit("parent", name="parent", parent=grandparent)
    grandchild = plant.unit("grandchild", name="grandchild", parent=parent)
    _site(plant, Site("rack-a1", "mod-g", "G1", 1, grandparent))
    (near,) = _site(plant, Site("rack-p9", "mod-p", "P1", 1, parent))
    device = _device(plant, "dev-g", grandchild)
    model, findings = allocate_plc(plant.model())
    assert findings == ()
    assert _bound(model) == {device: near}


def test_an_exhausted_ancestor_queue_does_not_fall_on_to_the_grandparent_or_top_level() -> None:
    """The parent's one channel goes to the first request; the second falls no further."""
    plant = Plant()
    grandparent = plant.unit("grandparent", name="grandparent")
    parent = plant.unit("parent", name="parent", parent=grandparent)
    grandchild = plant.unit("grandchild", name="grandchild", parent=parent)
    _site(plant, Site("rack-a1", "mod-g", "G1", 2, grandparent))
    _site(plant, Site("rack-a2", "mod-t", "T1", 2))
    (near,) = _site(plant, Site("rack-p9", "mod-p", "P1", 1, parent))
    first = _device(plant, "dev-1", grandchild, priority=1)
    second = _device(plant, "dev-2", grandchild, priority=2)
    model, (finding,) = allocate_plc(plant.model())
    assert _bound(model) == {first: near}
    assert finding.code == PLC_REQUEST_UNSERVABLE
    assert second in finding.subjects
    assert "taken" in finding.message
    assert "declares no" not in finding.message


def test_a_cabinet_serving_from_its_own_subtree_lists_the_same_alone_and_in_a_system() -> None:
    """`cab` holds the rack, its child falls through to it; a sibling rack sorting first: moot."""

    def build(*, with_system: bool) -> tuple[Model, Id[Unit]]:
        plant = Plant()
        cab = plant.unit("cab", name="cab")
        child = plant.unit("child", name="child", parent=cab)
        channels = _site(plant, Site("rack-b2", "mod-cab", "A1", 2, cab))
        _device(plant, "dev-cab", cab, channel=channels[0])
        _device(plant, "dev-child", child, channel=channels[1])
        if with_system:
            other = plant.unit("other", name="other")
            _site(plant, Site("rack-a1", "mod-other", "A2", 2, other))
        model, findings = allocate_plc(plant.model())
        assert findings == ()
        return model, cab

    columns = ("channel_designation", "signal", "wired_to", "field_device_designation")
    columns += ("signal_name",)

    def rows(model: Model, cab: Id[Unit]) -> list[tuple[object, ...]]:
        return [
            tuple(getattr(row, column) for column in columns)
            for row in plc_channel_rows(model, unit=cab)
        ]

    alone_rows = rows(*build(with_system=False))
    system_rows = rows(*build(with_system=True))
    assert len(alone_rows) == 2
    assert system_rows == alone_rows
