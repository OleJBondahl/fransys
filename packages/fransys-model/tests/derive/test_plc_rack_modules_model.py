"""Tests for `plc_rack_modules` (design/derive-queries.md)."""

from decimal import Decimal

import pytest
from plant import Plant
from query_builders import bind_device, reversed_tables
from rack_builders import make_module, scale

from fransys_model.derive import ChannelScaling, allocate_plc, plc_channel_rows, plc_rack_modules
from fransys_model.kernel import Id, SchemaError, make_id
from fransys_model.vocab.core import Item
from fransys_model.vocab.enums import PartCategory, SignalType
from fransys_model.vocab.facets.plc import PlcBindingFacet, PlcRequestFacet
from fransys_model.vocab.tables import facets_of

_DI = SignalType.DI
_AI = SignalType.AI_CURRENT


def _rack(plant: Plant) -> Id[Item]:
    return plant.item("rack", designation="R1")


def test_modules_are_ordered_by_position_then_none_last_by_key() -> None:
    """Authored out of order: `1`, `2`, then the unpositioned ones by key."""
    plant = Plant()
    rack = _rack(plant)
    for key, position in (("m-d", None), ("m-c", 2), ("m-a", None), ("m-b", 1)):
        make_module(
            plant, rack, key, part="di", signals=(_DI,), position=position, designation=key.upper()
        )
    rows = plc_rack_modules(plant.model(), rack)
    assert [(row.designation, row.position) for row in rows] == [
        ("-M-B", 1),
        ("-M-C", 2),
        ("-M-A", None),
        ("-M-D", None),
    ]


def test_the_order_is_the_one_allocation_serves_the_modules_in() -> None:
    """One request per module, in priority order, lands on the modules in rack order."""
    plant = Plant()
    rack = _rack(plant)
    layout = (("m-d", None), ("m-c", 5), ("m-a", None), ("m-b", 1), ("m-e", 3))
    for key, position in layout:
        make_module(plant, rack, key, part="di", signals=(_DI,), position=position, designation=key)
    for priority in range(1, len(layout) + 1):
        device = plant.function(plant.item(f"dev{priority}", designation=f"D{priority}"), "signal")
        plant.add(
            PlcRequestFacet(
                id=make_id(PlcRequestFacet, (f"dev{priority}", "request")),
                key=(f"dev{priority}", "request"),
                subject=device,
                signal=_DI,
                signal_name=f"tag{priority}",
                priority=priority,
            )
        )
    model = plant.model()
    allocated, findings = allocate_plc(model)
    assert findings == ()
    rows = plc_rack_modules(model, rack)
    module_of = {channel.channel: row.module for row in rows for channel in row.channels}
    channel_of = {
        binding.subject: binding.channel
        for binding in facets_of(allocated, PlcBindingFacet).values()
    }
    requests = sorted(facets_of(model, PlcRequestFacet).values(), key=lambda r: r.priority)
    assert [module_of[channel_of[request.subject]] for request in requests] == [
        row.module for row in rows
    ]


def test_two_modules_of_one_part_are_two_rows_with_the_parts_fields() -> None:
    """`mpn` and `description` are the part's; each module has its own channels."""
    plant = Plant()
    rack = _rack(plant)
    for key, position in (("m-1", 1), ("m-2", 2)):
        make_module(
            plant, rack, key, part="di8", signals=(_DI, _DI), position=position, designation=key
        )
    first, second = plc_rack_modules(plant.model(), rack)
    assert (first.mpn, first.description) == ("MPN-di8", "Invented di8")
    assert (second.mpn, second.description) == (first.mpn, first.description)
    assert (first.module, second.module) == (make_id(Item, ("m-1",)), make_id(Item, ("m-2",)))
    assert {channel.channel for channel in first.channels}.isdisjoint(
        channel.channel for channel in second.channels
    )
    assert [channel.number for channel in second.channels] == [1, 2]


def test_every_channel_is_listed_bound_or_spare_in_channel_order() -> None:
    """`1` bound, `2` spare, `3` bound; the spare channel has `None` for every field device."""
    plant = Plant()
    rack = _rack(plant)
    _, channels = make_module(
        plant, rack, "m-1", part="mix", signals=(_DI, _AI, _DI), position=1, designation="A1"
    )
    device = bind_device(plant, "dev", "B7", channels[2])
    (row,) = plc_rack_modules(plant.model(), rack)
    assert [(c.number, c.signal) for c in row.channels] == [(1, _DI), (2, _AI), (3, _DI)]
    spare, bound = row.channels[0], row.channels[2]
    assert (spare.field_device, spare.field_device_designation) == (None, None)
    assert (spare.signal_name, spare.scaling) == (None, None)
    assert (bound.field_device, bound.field_device_designation) == (device, "-B7")
    assert bound.signal_name == "tag_dev"
    assert bound.scaling is None


def test_a_bound_device_with_a_scaling_facet_projects_it() -> None:
    """Unit, raw range and engineering range come from the device's `scaling` facet."""
    plant = Plant()
    rack = _rack(plant)
    _, channels = make_module(
        plant, rack, "m-1", part="ai", signals=(_AI,), position=1, designation="A1"
    )
    scale(plant, bind_device(plant, "dev", "B7", channels[0]), "dev")
    (row,) = plc_rack_modules(plant.model(), rack)
    assert row.channels[0].scaling == ChannelScaling(
        unit="percent", raw_min=4, raw_max=20, eng_min=Decimal(0), eng_max=Decimal(100)
    )


def test_the_field_side_is_what_plc_channel_rows_reads() -> None:
    """Device, designation and signal name agree with `plc_channel_rows`, channel by channel."""
    plant = Plant()
    rack = _rack(plant)
    _, channels = make_module(
        plant, rack, "m-1", part="di", signals=(_DI, _DI), position=1, designation="A1"
    )
    bind_device(plant, "dev", "B7", channels[1])
    model = plant.model()
    by_channel = {row.channel: row for row in plc_channel_rows(model)}
    for channel in plc_rack_modules(model, rack)[0].channels:
        row = by_channel[channel.channel]
        assert (channel.field_device, channel.field_device_designation, channel.signal_name) == (
            row.field_device,
            row.field_device_designation,
            row.signal_name,
        )
        assert channel.signal is row.signal


def test_a_channel_named_by_two_bindings_takes_the_smallest_device_id() -> None:
    """Two devices bound to one channel: the smaller function id is the field device."""
    plant = Plant()
    rack = _rack(plant)
    _, channels = make_module(
        plant, rack, "m-1", part="di", signals=(_DI,), position=1, designation="A1"
    )
    devices = [bind_device(plant, key, key.upper(), channels[0]) for key in ("dev-x", "dev-y")]
    (row,) = plc_rack_modules(plant.model(), rack)
    assert row.channels[0].field_device == min(devices)


def test_a_module_without_channels_is_listed_with_none() -> None:
    """A coupler of category `PLC_MODULE` and no channel template is a row with `channels=()`."""
    plant = Plant()
    rack = _rack(plant)
    make_module(plant, rack, "coupler", part="cpl", signals=(), position=0, designation="A0")
    (row,) = plc_rack_modules(plant.model(), rack)
    assert (row.designation, row.channels) == ("-A0", ())


def test_only_plc_module_children_of_the_rack_are_listed() -> None:
    """Another category, a part-less child, a module of another rack and the rack itself: none."""
    plant = Plant()
    rack = _rack(plant)
    make_module(plant, rack, "mod", part="di", signals=(_DI,), position=1, designation="A1")
    make_module(
        plant,
        rack,
        "misc",
        part="misc",
        signals=(_DI,),
        position=2,
        designation="A2",
        category=PartCategory.GENERIC,
    )
    plant.item("bare", parent=rack, designation="A3")
    other = plant.item("rack-2", designation="R2")
    make_module(plant, other, "elsewhere", part="di", signals=(_DI,), position=1, designation="B1")
    rows = plc_rack_modules(plant.model(), rack)
    assert [row.designation for row in rows] == ["-A1"]


def test_an_uninstalled_module_is_listed_like_any_other() -> None:
    """`installed` is ignored, as `allocate_plc` ignores it."""
    plant = Plant()
    rack = _rack(plant)
    make_module(
        plant, rack, "mod", part="di", signals=(_DI,), position=1, designation="A1", installed=False
    )
    (row,) = plc_rack_modules(plant.model(), rack)
    assert row.designation == "-A1"


def test_a_module_or_device_without_a_designation_raises() -> None:
    """The designations are rendered, so they must exist."""
    plant = Plant()
    rack = _rack(plant)
    make_module(plant, rack, "mod", part="di", signals=(_DI,), position=1, designation=None)
    with pytest.raises(SchemaError):
        plc_rack_modules(plant.model(), rack)
    plant = Plant()
    rack = _rack(plant)
    _, channels = make_module(
        plant, rack, "mod", part="di", signals=(_DI,), position=1, designation="A1"
    )
    bind_device(plant, "dev", None, channels[0])
    with pytest.raises(SchemaError):
        plc_rack_modules(plant.model(), rack)


def test_a_rack_that_is_not_an_item_raises() -> None:
    """The refusal every query gives for an identity id the model does not hold."""
    with pytest.raises(SchemaError):
        plc_rack_modules(Plant().model(), Id(kind="item", value="9" * 32))


def test_a_rack_that_is_not_an_item_raises_naming_the_rack() -> None:
    """The refusal's `.kind` is `"item"` and `.record_id` is the rack id given."""
    unknown = Id(kind="item", value="9" * 32)
    with pytest.raises(SchemaError) as excinfo:
        plc_rack_modules(Plant().model(), unknown)
    assert (excinfo.value.kind, excinfo.value.record_id) == ("item", unknown)


def test_a_rack_with_no_children_at_all_is_empty_not_a_crash() -> None:
    """A real rack item that has no children (no entry in the child index) still returns `()`."""
    plant = Plant()
    rack = plant.item("rack", designation="A1")
    assert plc_rack_modules(plant.model(), rack) == ()


def test_modules_out_of_input_order_still_sort_ascending_none_last() -> None:
    """Position `2` authored before position `1`: the row order is still ascending, `None` last."""
    plant = Plant()
    rack = _rack(plant)
    for key, position in (("m-second", 2), ("m-first", 1), ("m-unpositioned", None)):
        make_module(plant, rack, key, part="di", signals=(_DI,), position=position, designation=key)
    rows = plc_rack_modules(plant.model(), rack)
    assert [(row.designation, row.position) for row in rows] == [
        ("-m-first", 1),
        ("-m-second", 2),
        ("-m-unpositioned", None),
    ]


def test_a_function_with_no_plc_channel_facet_leaves_channels_empty() -> None:
    """A function that carries no `plc_channel` facet at all: the row still has `channels=()`."""
    plant = Plant()
    rack = _rack(plant)
    module, _ = make_module(
        plant, rack, "m-1", part="misc", signals=(), position=1, designation="A1"
    )
    plant.function(module, "status")
    (row,) = plc_rack_modules(plant.model(), rack)
    assert row.channels == ()


def test_a_non_channel_function_ahead_of_a_channel_does_not_hide_it() -> None:
    """A function with no channel facet, ordered before the real channel by id, is just skipped."""
    plant = Plant()
    rack = _rack(plant)
    module, channels = make_module(
        plant, rack, "m-1", part="di", signals=(_DI,), position=1, designation="A1"
    )
    plant.function(module, "aux")
    (row,) = plc_rack_modules(plant.model(), rack)
    assert [channel.channel for channel in row.channels] == channels


def test_the_rows_do_not_depend_on_table_order() -> None:
    """The tables backwards, under another digest, give the same rows."""
    plant = Plant()
    rack = _rack(plant)
    _, channels = make_module(
        plant, rack, "m-1", part="mix", signals=(_DI, _AI), position=None, designation="A1"
    )
    make_module(plant, rack, "m-2", part="mix", signals=(_DI, _AI), position=1, designation="A2")
    scale(plant, bind_device(plant, "dev", "B7", channels[1]), "dev")
    model = plant.model()
    assert plc_rack_modules(reversed_tables(model), rack) == plc_rack_modules(model, rack)
