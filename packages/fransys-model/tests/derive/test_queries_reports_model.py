"""WP16 tests: BOM, PLC channel, cable, wire label and designation queries."""

import dataclasses
from decimal import Decimal

import pytest
from plant import Plant
from query_builders import (
    bind_device,
    make_channels,
    make_core,
    make_labelled,
    make_part,
    make_pin,
    make_plc,
    make_terminal,
    ports_against_ids,
    reversed_tables,
)

from fransys_model.derive import (
    bom_lines,
    cable_rows,
    designation_list,
    plc_channel_rows,
    wire_rows,
)
from fransys_model.derive.designation import (
    port_designation,
    reference_designation,
)
from fransys_model.kernel import Id, SchemaError, make_id
from fransys_model.vocab.connectivity import Conductor
from fransys_model.vocab.core import Item, Unit
from fransys_model.vocab.enums import (
    ConductorKind,
    SignalType,
)
from fransys_model.vocab.facets.cable import CoreFacet
from fransys_model.vocab.facets.terminal import TerminalFacet
from fransys_model.vocab.facets.wire import WireFacet
from fransys_model.vocab.templates import Part


def test_bom_lines_group_installed_items_by_part_and_sort_designations_as_strings() -> None:
    """Count is the installed items; `K10` sorts before `K2` (whole strings, nothing parsed)."""
    plant = Plant()
    relay = make_part(plant, "relay", "R-1")
    plant.item("k2", part=relay, designation="K2")
    plant.item("k10", part=relay, designation="K10")
    plant.item("k3", part=relay, designation="K3", installed=False)
    (line,) = bom_lines(plant.model())
    assert (line.part, line.mpn, line.manufacturer, line.description) == (
        relay,
        "R-1",
        "Example Co",
        "Invented relay",
    )
    assert line.count == 2
    assert line.designations == ("-K10", "-K2")


def test_bom_lines_leave_out_uninstalled_only_parts_and_items_without_a_part() -> None:
    """No installed item, no line; an item with no part has no MPN and no line.

    An uninstalled item is never asked for a designation.
    """
    plant = Plant()
    plant.item("ghost", part=make_part(plant, "ghost", "G-1"), installed=False)
    plant.item("bare", designation="X1")
    assert bom_lines(plant.model()) == ()


def test_bom_lines_are_sorted_by_mpn_then_part_id() -> None:
    """The MPN ranks before the part id; two parts with one MPN order by id."""
    plant = Plant()
    low, middle, high = sorted(("part-a", "part-b", "part-c"), key=lambda k: make_id(Part, (k,)))
    for key, mpn in ((high, "A-FIRST"), (low, "SAME"), (middle, "SAME")):
        plant.item(f"i-{key}", part=make_part(plant, key, mpn), designation=key.upper())
    lines = bom_lines(plant.model())
    assert [line.mpn for line in lines] == ["A-FIRST", "SAME", "SAME"]
    assert [line.part for line in lines] == [
        make_id(Part, (high,)),
        make_id(Part, (low,)),
        make_id(Part, (middle,)),
    ]


def test_bom_lines_refuse_an_installed_item_without_a_designation() -> None:
    """The designation is rendered, so it must exist."""
    plant = Plant()
    plant.item("k1", part=make_part(plant, "relay", "R-1"))
    with pytest.raises(SchemaError):
        bom_lines(plant.model())


def _terminal_item(  # noqa: PLR0913 -- one param per field the tests vary, kept explicit
    plant: Plant, key: str, *, strip: Id[Item], part: Id[Part], group: str, index: int
) -> None:
    """One installed terminal of `strip`, carrying a `TerminalFacet` (decision model-0050)."""
    item = plant.item(key, parent=strip, part=part, designation=f"{group}:{index}")
    plant.add(
        TerminalFacet(
            id=make_id(TerminalFacet, (key, "facet")),
            key=(key, "facet"),
            subject=item,
            group=group,
            index=index,
        )
    )


def test_two_strips_sharing_a_bare_terminal_designation_have_distinct_bom_designations() -> None:
    """A BOM designation for a terminal is `<strip>:<terminal>`, sorted by strip, group, index.

    `X1` and `X01` each have an `L1:1` terminal (the designer's own worked example, the fault
    decision model-0046 fixed for cable ends): without the strip prefix, both terminals would
    print the identical bare text `"L1:1"` twice in one BOM line and name neither.
    """
    plant = Plant()
    part = make_part(plant, "terminal", "SIM-TERMINAL-2.5MM")
    x1 = plant.item("x1", designation="X1")
    x01 = plant.item("x01", designation="X01")
    _terminal_item(plant, "x1-l1-1", strip=x1, part=part, group="L1", index=1)
    _terminal_item(plant, "x01-l1-1", strip=x01, part=part, group="L1", index=1)
    (line,) = bom_lines(plant.model())
    assert line.designations == ("-X01:L1:1", "-X1:L1:1")
    assert len(set(line.designations)) == 2


def test_bom_terminal_designations_sort_by_strip_then_group_then_index_numerically() -> None:
    """Two terminals of one strip, `L1:2` and `L1:10`, sort by index, not as strings."""
    plant = Plant()
    part = make_part(plant, "terminal", "SIM-TERMINAL-2.5MM")
    strip = plant.item("x1", designation="X1")
    _terminal_item(plant, "x1-l1-10", strip=strip, part=part, group="L1", index=10)
    _terminal_item(plant, "x1-l1-2", strip=strip, part=part, group="L1", index=2)
    (line,) = bom_lines(plant.model())
    assert line.designations == ("-X1:L1:2", "-X1:L1:10")


def test_plc_channel_rows_fill_every_field_for_a_bound_channel() -> None:
    """Device, its signal name, and where the channel's own port is wired (the terminal)."""
    plant = Plant()
    channels, device, terminal = make_plc(plant)
    plant.wire(plant.port(channels[0], "1"), terminal.internal, key="channel-wire")
    model = plant.model()
    row = next(r for r in plc_channel_rows(model) if r.channel == channels[0])
    assert row.channel_designation == "-A1:1"
    assert row.signal is SignalType.DI
    assert row.field_device == device
    assert row.field_device_designation == "-B7"
    assert row.signal_name == "tag_dev"
    assert row.wired_to == port_designation(model, terminal.internal)


def test_plc_channel_rows_of_an_unbound_channel_have_every_device_field_none() -> None:
    """The signal of the channel is still reported, per channel, not one type for all."""
    plant = Plant()
    channels, _, _ = make_plc(plant)
    rows = {r.channel: r for r in plc_channel_rows(plant.model())}
    row = rows[channels[1]]
    assert row.channel_designation == "-A1:2"
    assert row.signal is SignalType.AI_CURRENT
    assert (row.field_device, row.field_device_designation, row.signal_name) == (None,) * 3
    assert row.wired_to is None


def test_plc_channel_rows_hold_channels_only_and_sort_by_designation_as_a_string() -> None:
    """`A10` before `A2` (whole strings); functions that are not channels are not rows."""
    plant = Plant()
    make_channels(plant, "m-two", "A2", (SignalType.DI,))
    make_channels(plant, "m-ten", "A10", (SignalType.DI, SignalType.DI))
    plant.function(plant.item("dev", designation="B1"), "signal")
    rows = plc_channel_rows(plant.model())
    assert [r.channel_designation for r in rows] == ["-A10:1", "-A10:2", "-A2:1"]


def test_plc_channel_rows_take_the_smallest_id_device_when_two_are_bound() -> None:
    """A doubly bound channel is `PLC_CHANNEL_DOUBLE_BOUND`'s business; the row is deterministic."""
    plant = Plant()
    (channel,) = make_channels(plant, "mod", "A1", (SignalType.DI,))
    first = bind_device(plant, "dev-a", "B1", channel)
    second = bind_device(plant, "dev-b", "B2", channel)
    (row,) = plc_channel_rows(plant.model())
    assert row.field_device == min(first, second)


def test_plc_channel_rows_refuse_a_module_without_a_designation() -> None:
    """The channel designation is rendered from the module's."""
    plant = Plant()
    make_channels(plant, "mod", None, (SignalType.DI,))
    with pytest.raises(SchemaError):
        plc_channel_rows(plant.model())


def test_plc_channel_rows_refuse_a_field_device_without_a_designation() -> None:
    """The device designation is rendered too, not only the module's."""
    plant = Plant()
    (channel,) = make_channels(plant, "mod", "A1", (SignalType.DI,))
    bind_device(plant, "dev", None, channel)
    with pytest.raises(SchemaError):
        plc_channel_rows(plant.model())


def test_cable_rows_and_wire_rows_refuse_an_end_without_a_designation() -> None:
    """The port designations are rendered from the ends' items."""
    plant = Plant()
    cable = plant.item("w1", designation="W1")
    numbered = make_pin(plant, "a", "B1")
    bare = make_pin(plant, "b", None)
    make_core(plant, "core", cable, (numbered, bare), index=1)
    make_labelled(plant, "lab", numbered, bare, "L1")
    model = plant.model()
    with pytest.raises(SchemaError):
        cable_rows(model, cable)
    with pytest.raises(SchemaError):
        wire_rows(model)


def test_cable_rows_list_the_cores_of_the_cable_ordered_by_core_index() -> None:
    """Both ends rendered as port designations; index and colour from the core facet."""
    plant = Plant()
    cable = plant.item("w1", designation="W1")
    a1, a2, b1, b2 = (
        make_pin(plant, k, d) for k, d in (("a1", "B1"), ("a2", "B2"), ("b1", "X1"), ("b2", "X2"))
    )
    late = make_core(plant, "core-first-authored", cable, (a2, b2), index=2)
    early = make_core(plant, "core-second-authored", cable, (a1, b1), index=1)
    model = plant.model()
    rows = cable_rows(model, cable)
    assert [row.conductor for row in rows] == [early, late]
    first = rows[0]
    assert (first.cable, first.cable_designation) == (cable, "-W1")
    assert (first.index, first.colour) == (1, "colour-1")
    assert (first.end_a, first.end_b) == (a1, b1)
    assert first.end_a_designation == port_designation(model, a1)
    assert first.end_b_designation == port_designation(model, b1)


def test_cable_rows_leave_out_other_cables_wires_and_a_core_without_a_facet() -> None:
    """Only `core` conductors that name this cable and carry a `core` facet."""
    plant = Plant()
    cable = plant.item("w1", designation="W1")
    other = plant.item("w2", designation="W2")
    a, b, c, d, e, f = (make_pin(plant, f"p{i}", f"P{i}") for i in range(6))
    kept = make_core(plant, "kept", cable, (a, b), index=1)
    make_core(plant, "theirs", other, (c, d), index=1)
    plant.core(e, f, key="no-facet", carrier=cable)
    plant.wire(a, c, key="plain-wire")
    stray = Conductor(
        id=make_id(Conductor, ("stray",)),
        key=("stray",),
        a=c,
        b=e,
        kind=ConductorKind.WIRE,
        carrier=cable,
    )
    plant.add(
        stray,
        CoreFacet(
            id=make_id(CoreFacet, ("stray", "facet")),
            key=("stray", "facet"),
            subject=stray.id,
            index=9,
        ),
    )
    assert [row.conductor for row in cable_rows(plant.model(), cable)] == [kept]


def test_cable_rows_tie_on_core_index_orders_by_conductor_id() -> None:
    """Two cores claiming one index still come out in a fixed order."""
    plant = Plant()
    cable = plant.item("w1", designation="W1")
    made = [
        make_core(
            plant,
            f"c{i}",
            cable,
            (make_pin(plant, f"a{i}", f"A{i}"), make_pin(plant, f"b{i}", f"B{i}")),
            index=1,
        )
        for i in range(4)
    ]
    model = plant.model()
    for m in (model, reversed_tables(model)):
        assert [row.conductor for row in cable_rows(m, cable)] == sorted(made)


def test_cable_rows_refuse_an_id_that_is_not_an_item() -> None:
    """Unknown cable: `SchemaError`."""
    plant = Plant()
    plant.item("w1", designation="W1")
    with pytest.raises(SchemaError):
        cable_rows(plant.model(), make_id(Item, ("nope",)))


def test_wire_rows_sort_by_the_from_end_then_the_to_end_not_the_id() -> None:
    """The order follows the printed ends, whatever the conductor ids are.

    The ends print in the fixed end order (V8), never the order the conductor stores them, and
    the conductor ids are arranged to run against the designations.
    """
    plant = Plant()
    ports = ports_against_ids(plant, 6)
    ids_high_first = sorted(
        ("w-a", "w-b", "w-c"), key=lambda k: make_id(Conductor, (k,)), reverse=True
    )
    first = make_labelled(plant, ids_high_first[0], ports[0], ports[1], "A")  # authored K2 -> K1
    second = make_labelled(plant, ids_high_first[1], ports[1], ports[2], "A")  # authored K3 -> K2
    third = make_labelled(plant, ids_high_first[2], ports[3], ports[4], "A")  # authored K5 -> K4
    rows = wire_rows(plant.model())
    assert [row.conductor for row in rows] == [first, second, third]
    assert [(row.from_, row.to) for row in rows] == [
        ("-K1:1", "-K2:1"),
        ("-K2:1", "-K3:1"),
        ("-K4:1", "-K5:1"),
    ]


def test_wire_rows_hold_only_wire_faceted_conductors() -> None:
    """A conductor with no `wire` facet is not in the wire list."""
    plant = Plant()
    a, b, c = (make_pin(plant, f"i{n}", f"K{n}") for n in (1, 2, 3))
    kept = make_labelled(plant, "w1", a, b, "L1")
    plant.wire(b, c, key="bare")
    assert [row.conductor for row in wire_rows(plant.model())] == [kept]


def test_wire_rows_with_the_same_two_ends_fall_to_the_conductor_id() -> None:
    """Same `from_` and same `to`: the conductor id decides."""
    plant = Plant()
    hub, other = ports_against_ids(plant, 2)
    made = [make_labelled(plant, f"w{n}", hub, other, None) for n in range(4)]
    rows = wire_rows(plant.model())
    assert [row.conductor for row in rows] == sorted(made)
    assert {(row.from_, row.to) for row in rows} == {("-K1:1", "-K2:1")}
    assert {row.label for row in rows} == {"-K1:1 -K2:1"}


def test_designation_list_has_every_item_terminals_included_sorted_as_strings() -> None:
    """`-K10` before `-K2`; the reference form and description are carried; nothing is parsed.

    The terminal's designation is `terminal_designation` (`"-X1:L:1"`, decision model-0052)
    and every other item is dashed too (decision model-0054): one uniform string sort.
    """
    plant = Plant()
    plant.item("k2", designation="K2")
    parent = plant.item("a1", designation="A1")
    plant.item("k10", designation="K10", parent=parent)
    plant.item("x1", designation="X1")
    terminal = make_terminal(plant, "x1", "t1", group="L", index=1)
    model = plant.model()
    rows = designation_list(model)
    assert [row.designation for row in rows] == ["-A1", "-K10", "-K2", "-X1", "-X1:L:1"]
    by_item = {row.item: row for row in rows}
    assert terminal.item in by_item
    for row in rows:
        assert row.reference == reference_designation(model, row.item)
        assert row.description == "Invented"


def test_designation_list_ties_on_designation_fall_to_the_item_id() -> None:
    """The same designation on two items (board and cabinet `F1`): the id orders them."""
    plant = Plant()
    plant.item("f-a", designation="F1")
    plant.item("f-b", designation="F1")
    rows = designation_list(plant.model())
    assert [row.item for row in rows] == sorted(make_id(Item, (k,)) for k in ("f-a", "f-b"))


def test_designation_list_refuses_an_unnumbered_item() -> None:
    """A designation still `None` cannot be listed."""
    plant = Plant()
    plant.item("k1")
    with pytest.raises(SchemaError):
        designation_list(plant.model())


# ---- units spec U6: the unit scope of plc_channel_rows, wire_rows, designation_list -----


def _nested_units(plant: Plant) -> tuple[Id[Unit], Id[Unit]]:
    """`u1` nests `u2` (not siblings): the case that tells direct membership from `unit_subtree`."""
    u1 = plant.unit("u1", name="cabinet", revision=1)
    plant.revision(u1)
    u2 = plant.unit("u2", name="board", revision=1, parent=u1)
    plant.revision(u2)
    return u1, u2


def _set_unit(plant: Plant, item_id: Id[Item], unit: Id[Unit]) -> None:
    """Give an already-added item `unit` (records are frozen; replaced in place)."""
    record = next(r for r in plant.records if r.id == item_id)
    plant.records.remove(record)
    plant.add(dataclasses.replace(record, unit=unit))


def test_plc_channel_rows_with_a_unit_keep_only_that_units_own_channels() -> None:
    """A channel of a module in `u1` is kept; `u2`'s and an unowned module's are not.

    The unscoped call sees all three; the scoped call is a strict, named-count subset of it.
    """
    plant = Plant()
    u1, u2 = _nested_units(plant)
    (ch1,) = make_channels(plant, "mod1", "A1", (SignalType.DI,))
    (ch2,) = make_channels(plant, "mod2", "A2", (SignalType.DI,))
    (ch3,) = make_channels(plant, "mod3", "A3", (SignalType.DI,))
    _set_unit(plant, make_id(Item, ("mod1",)), u1)
    _set_unit(plant, make_id(Item, ("mod2",)), u2)
    model = plant.model()
    unscoped = plc_channel_rows(model)
    assert len(unscoped) == 3
    assert {r.channel for r in unscoped} == {ch1, ch2, ch3}
    rows = plc_channel_rows(model, unit=u1)
    assert [r.channel for r in rows] == [ch1]
    # can-fail probe: a nested unit's own channel must never sneak into the parent's rows
    assert ch2 not in {r.channel for r in rows}


def test_designation_list_with_a_unit_keeps_only_that_units_own_items() -> None:
    """Direct membership only: `u2`'s item and the unowned item are both left out.

    The unscoped call sees all four; the scoped call is a strict, named-count subset of it.
    `u1` holds two root items: a sole root is silent in its own scope (UNIT-ID I4).
    """
    plant = Plant()
    u1, u2 = _nested_units(plant)
    plant.item("a", designation="A1", unit=u1)
    plant.item("a2", designation="A2", unit=u1)
    plant.item("b", designation="B1", unit=u2)
    plant.item("c", designation="C1")
    model = plant.model()
    unscoped = designation_list(model)
    assert len(unscoped) == 4
    assert {row.designation for row in unscoped} == {"-A1", "-A2", "-B1", "-C1"}
    rows = designation_list(model, unit=u1)
    assert [row.designation for row in rows] == ["-A1", "-A2"]


def test_wire_rows_with_a_unit_include_a_wire_crossing_into_a_nested_unit() -> None:
    """A wire from a cabinet's own item to a nested board's item belongs to the cabinet.

    Units spec U6, amended 2026-09-23: a conductor belongs to the *lowest* unit whose
    subtree holds both ends' items, not to a unit only when both ends belong to it directly,
    and not to *every* common ancestor either. The designer's own two examples: a wire from
    a cabinet terminal to a board connector, the board nested in the cabinet, belongs to the
    cabinet; a wire inside the board belongs to the board, not also to the cabinet -- this
    second example is what tells "lowest" apart from "every ancestor", and is the reason a
    board-internal wire must not leak into the cabinet's own `wire-labels.csv`. The unscoped
    call sees all three wires; each scoped call is a strict, named-count subset of it.
    """
    plant = Plant()
    cabinet, board = _nested_units(plant)
    cabinet_end = make_pin(plant, "cabinet-end", "X1")
    board_end = make_pin(plant, "board-end", "X2")
    other_cabinet_end = make_pin(plant, "other-cabinet-end", "X3")
    other_board_end = make_pin(plant, "other-board-end", "X4")
    _set_unit(plant, make_id(Item, ("cabinet-end",)), cabinet)
    _set_unit(plant, make_id(Item, ("board-end",)), board)
    _set_unit(plant, make_id(Item, ("other-cabinet-end",)), cabinet)
    _set_unit(plant, make_id(Item, ("other-board-end",)), board)
    crossing = make_labelled(plant, "w-crossing", cabinet_end, board_end, "L1")
    within_cabinet = make_labelled(plant, "w-within-cabinet", cabinet_end, other_cabinet_end, "L2")
    within_board = make_labelled(plant, "w-within-board", board_end, other_board_end, "L3")
    model = plant.model()
    unscoped = wire_rows(model)
    assert len(unscoped) == 3
    assert {row.conductor for row in unscoped} == {crossing, within_cabinet, within_board}
    in_cabinet = wire_rows(model, unit=cabinet)
    in_board = wire_rows(model, unit=board)
    assert len(in_cabinet) == 2
    assert {row.conductor for row in in_cabinet} == {crossing, within_cabinet}
    # can-fail probe: a wire wholly inside the nested unit must never leak into the parent's
    assert within_board not in {row.conductor for row in in_cabinet}
    assert len(in_board) == 1
    assert {row.conductor for row in in_board} == {within_board}
    # can-fail probe: the crossing wire must never sneak into the nested unit's own rows
    assert crossing not in {row.conductor for row in in_board}


def test_wire_rows_with_a_unit_exclude_a_wire_touching_an_unowned_item() -> None:
    """A wire with one end that belongs to no unit at all belongs to no unit either."""
    plant = Plant()
    u1, _u2 = _nested_units(plant)
    owned = make_pin(plant, "owned", "A1")
    loose = make_pin(plant, "loose", "X1")
    _set_unit(plant, make_id(Item, ("owned",)), u1)
    excluded = make_labelled(plant, "w-loose", owned, loose, "L1")
    model = plant.model()
    rows = wire_rows(model, unit=u1)
    assert excluded not in {row.conductor for row in rows}


def test_wire_rows_with_a_unit_leave_out_a_core_even_when_its_carrier_belongs() -> None:
    """A `core`-kind, `wire`-faceted conductor is no wire-list row, whatever unit holds its carrier.

    The cable's cores are `cable_rows`; the one WIRE in `u1` is the only row.
    """
    plant = Plant()
    u1, u2 = _nested_units(plant)
    cable = plant.item("cbl", designation="W1", unit=u1)
    far_a = make_pin(plant, "far-a", "P1")
    far_b = make_pin(plant, "far-b", "P2")
    _set_unit(plant, make_id(Item, ("far-a",)), u2)
    _set_unit(plant, make_id(Item, ("far-b",)), u2)
    core = plant.core(far_a, far_b, key="core", carrier=cable)
    plant.add(
        WireFacet(
            id=make_id(WireFacet, ("core", "facet")),
            key=("core", "facet"),
            subject=core,
            colour="black",
            gauge_mm2=Decimal("0.75"),
            length_mm=None,
            label="L9",
        )
    )
    near_a = make_pin(plant, "near-a", "P3")
    near_b = make_pin(plant, "near-b", "P4")
    _set_unit(plant, make_id(Item, ("near-a",)), u1)
    _set_unit(plant, make_id(Item, ("near-b",)), u1)
    wire = make_labelled(plant, "w-near", near_a, near_b, "L8")
    rows = wire_rows(plant.model(), unit=u1)
    assert core not in {row.conductor for row in rows}
    assert [row.conductor for row in rows] == [wire]


def test_unit_scoped_row_queries_refuse_an_unknown_unit() -> None:
    """A unit id the model does not hold is refused by all three, the same `require` pattern."""
    plant = Plant()
    plant.item("a", designation="A1")
    model = plant.model()
    bad = Id(kind="unit", value="9" * 32)
    with pytest.raises(SchemaError):
        plc_channel_rows(model, unit=bad)
    with pytest.raises(SchemaError):
        wire_rows(model, unit=bad)
    with pytest.raises(SchemaError):
        designation_list(model, unit=bad)
