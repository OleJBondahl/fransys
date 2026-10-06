"""`RATING_CURRENT_BELOW_BRANCH` (RATINGS-2 C4 and its acceptance 1 to 5, decision model-0088).

Every device is an item `key` with one function `f` (builders in `current_plant`); a supply and
its rails are put on the string's first port, so `port_rails` reaches the whole line. The expected
values are written by hand from the spec, never copied from the output.
"""

from decimal import Decimal

import pytest
from current_plant import (
    bypass_plant,
    capped_changeover,
    changeover,
    contactor,
    device,
    external,
    fuse,
    hub,
    in_unit,
    mated,
    open_string,
    rate,
    run,
    sense_pin,
    shorted_when_closed,
    wire,
    with_role,
)
from plant import Plant
from rating_plant import rail, supply

from fransys_model.kernel import Finding, Severity, make_id
from fransys_model.vocab import (
    ALL_VALIDATORS,
    BoundaryValuesFacet,
    Operating,
    Rating,
    current_states,
)
from fransys_model.vocab.core import Port
from fransys_model.vocab.enums import Current, FunctionKind, LinkKind, PortRole
from fransys_model.vocab.validators import check_ratings, check_supplies
from fransys_model.vocab.validators.ratings_current import (
    RATING_CURRENT_BELOW_BRANCH,
    check_ratings_current,
)


def _dc_plant() -> Plant:
    plant = Plant()
    supply(plant, "dc", {"DC+": rail("985.5"), "DC-": rail("0")}, current=Current.DC)
    return plant


def _source(plant: Plant, key: str = "S", limit: str = "186", *, at: int = 1) -> tuple:
    """A source limited to `limit` A DC with DC+ on its port `at` (0 or 1), DC- on the other."""
    rails = [["DC-"], ["DC-"]]
    rails[at] = ["DC+"]
    return device(plant, key, limit=limit, rails=rails)


def _ids(*keys: str) -> set:
    return {Plant.function_id(key, "f") for key in keys}


def _fired(plant: Plant) -> set:
    return {finding.subjects[0] for finding in check_ratings_current(plant.model())}


def _the_finding(plant: Plant) -> Finding:
    (finding,) = check_ratings_current(plant.model())
    return finding


def _string(k_amps: str | None, *, fuse_amps: str = "400", partial: bool = True) -> Plant:
    """`S (186 A) - F (fuse) - K (contactor)`, both ends at external items (the outside)."""
    plant = _dc_plant()
    line = [fuse(plant, "F", fuse_amps, partial=partial), contactor(plant, "K", k_amps)]
    open_string(plant, _source(plant), line)
    return plant


# -- acceptance 1: the partial-range fuse bounds nothing --------------------------------------


def test_a_contactor_rated_below_the_source_limit_fires_with_the_full_message() -> None:
    finding = _the_finding(_string("150"))
    assert finding.code == RATING_CURRENT_BELOW_BRANCH == "RATING_CURRENT_BELOW_BRANCH"
    assert finding.severity is Severity.ERROR
    assert finding.subjects == (Plant.function_id("K", "f"),)
    assert finding.message == (
        "function 'f' of item K is rated 150 A DC (part or template rating), "
        "below its branch's 186 A DC set by the source of function 'f' of item S"
    )


def test_a_contactor_rated_at_or_above_the_limit_passes() -> None:
    assert check_ratings_current(_string("200").model()) == ()
    assert check_ratings_current(_string("186").model()) == ()  # equal passes


def test_a_partial_range_fuse_below_the_limit_is_itself_checked_and_bounds_nothing() -> None:
    """A 100 A partial fuse on the 186 A source: the 150 A contactor fires (bound 186 A), and so
    does the fuse, a rated device below the bound."""
    plant = _string("150", fuse_amps="100")
    found = check_ratings_current(plant.model())
    assert {f.subjects[0] for f in found} == _ids("F", "K")
    assert all("below its branch's 186 A DC set by the source" in f.message for f in found)


def test_the_source_is_compared_with_its_own_limit() -> None:
    """A source rated 100 A with a continuous limit of 186 A is below its own branch bound."""
    plant = _dc_plant()
    open_string(plant, device(plant, "S", amps="100", limit="186", rails=[[], ["DC+"]]), [])
    assert _fired(plant) == _ids("S")


# -- acceptance 2: a full-range fuse bounds the branch ---------------------------------------


def _fused(device_amps: str) -> Plant:
    """A 150 A source, a full-range 100 A fuse, a device rated `device_amps`."""
    plant = _dc_plant()
    line = [fuse(plant, "F", "100"), contactor(plant, "K", device_amps)]
    open_string(plant, _source(plant, limit="150"), line)
    return plant


def test_a_full_range_fuse_bounds_the_branch_at_its_own_rating() -> None:
    assert check_ratings_current(_fused("120").model()) == ()
    finding = _the_finding(_fused("90"))
    assert finding.subjects == (Plant.function_id("K", "f"),)
    assert finding.message.endswith(
        "below its branch's 100 A DC set by the protective device of function 'f' of item F"
    )


# -- acceptance 3: two strings on one bus ------------------------------------------------------


def test_no_strings_limit_bounds_the_devices_of_the_other_string() -> None:
    """String a is limited to 186 A and b to 90 A; `kb` (120 A) is above b's limit and below a's."""
    plant = _dc_plant()
    bus = hub(plant, "P")
    for tag, limit, amps in (("a", "186", "100"), ("b", "90", "120")):
        line = [fuse(plant, f"f{tag}"), contactor(plant, f"k{tag}", amps)]
        run(plant, bus, [*line, _source(plant, f"s{tag}", limit, at=0)], external(plant, f"T{tag}"))
    run(plant, bus, [device(plant, "feed", amps="300")], external(plant, "Tf"))
    assert _fired(plant) == _ids("ka")


# -- acceptance 3b to 3e: the reduction ---------------------------------------------------------


def _bypass(*, fuse_in_branch: bool = False) -> Plant:
    """`bypass_plant` on a DC supply, DC+ on the source's port 2."""
    plant = bypass_plant(fuse_in_branch=fuse_in_branch)
    supply(plant, "dc", {"DC+": rail("985.5"), "DC-": rail("0")}, current=Current.DC)
    plant.net("dc", (make_id(Port, ("S", "f", "2")),), potential="DC+")
    return plant


def test_the_far_end_plug_beyond_a_precharge_group_and_unrated_leads_is_checked() -> None:
    """Acceptance 3b: the plug (100 A) sits behind a precharge group, sense leads and a monitor."""
    plant = _bypass()
    found = check_ratings_current(plant.model())
    plug = next(f for f in found if f.subjects == (Plant.function_id("plug", "f"),))
    assert plug.message == (
        "function 'f' of item plug is rated 100 A DC (part or template rating), "
        "below its branch's 186 A DC set by the source of function 'f' of item S"
    )
    # Every rated device below 186 A fires, and no unrated one, the sense leads and the monitor.
    assert {f.subjects[0] for f in found} == _ids("K", "R", "PK", "plug", "Z")


def test_an_unrated_terminal_and_an_unrated_plug_do_not_cut_the_chain() -> None:
    """Acceptance 3c: a rated plug beyond an unrated terminal and an unrated plug is checked."""
    plant = _dc_plant()
    terminal = device(plant, "T", link=LinkKind.CONDUCTIVE, kind=FunctionKind.TERMINAL)
    plain, plain_socket = mated(plant, "plain", "plainsock")
    rated, rated_socket = mated(plant, "rated", "ratedsock", amps="100")
    source = _source(plant)
    wire(plant, source[0], external(plant, "T0"))
    run(plant, source[1], [contactor(plant, "K", "200"), terminal], plain)
    wire(plant, plain_socket, rated)
    load = device(plant, "Z", amps="300")
    wire(plant, rated_socket, load[0])
    wire(plant, load[1], external(plant, "T1"))
    assert _fired(plant) == _ids("rated")


def test_a_precharge_member_behind_its_own_fuse_is_bounded_by_it() -> None:
    """Acceptance 3d: `PK` (20 A) sits behind a 10 A fuse and passes; `R` (5 A) fires at 10 A;
    the main pole `K` (150 A) keeps the 186 A."""
    found = check_ratings_current(_bypass(fuse_in_branch=True).model())
    by_item = {f.subjects[0]: f.message for f in found}
    assert _ids("PK").isdisjoint(by_item)
    assert (
        "below its branch's 10 A DC set by the protective device"
        in by_item[Plant.function_id("R", "f")]
    )
    assert "below its branch's 186 A DC" in by_item[Plant.function_id("K", "f")]


def _two_strings_then_a_main_fuse() -> Plant:
    """Acceptance 3e: two 186 A strings between a + and a - bus, a 150 A main fuse on the + bus."""
    plant = _dc_plant()
    plus, minus = hub(plant, "P"), hub(plant, "M")
    for tag in ("a", "b"):
        line = [
            fuse(plant, f"f{tag}1"),
            contactor(plant, f"k{tag}1", "160"),
            _source(plant, f"s{tag}", at=0),
            contactor(plant, f"k{tag}2", "160"),
            fuse(plant, f"f{tag}2"),
        ]
        run(plant, plus, line, minus)
    # `X` is on the bus side of the main fuse; both feeders end at external items.
    run(
        plant,
        plus,
        [device(plant, "X", amps="120"), fuse(plant, "MF", "150")],
        external(plant, "Tp"),
    )
    run(plant, minus, [device(plant, "Y", amps="300")], external(plant, "Tm"))
    return plant


def test_the_main_fuse_bounds_the_bus_side_but_not_the_string_devices() -> None:
    plant = _two_strings_then_a_main_fuse()
    by_item = {f.subjects[0]: f.message for f in check_ratings_current(plant.model())}
    assert set(by_item) == _ids("ka1", "ka2", "kb1", "kb2", "X")
    for key in ("ka1", "ka2", "kb1", "kb2"):
        assert "rated 160 A DC" in by_item[Plant.function_id(key, "f")]
        assert (
            "below its branch's 186 A DC set by the source" in by_item[Plant.function_id(key, "f")]
        )
    assert (
        "below its branch's 150 A DC set by the protective device"
        in by_item[Plant.function_id("X", "f")]
    )


# -- acceptance 4: a nested unit's boundary limit ----------------------------------------------


def _unit_string(*, with_parent_device: bool, k_amps: str, inner_internal: bool = True) -> Plant:
    """A unit `u`: boundary `B` (limit 186 A on its Operating) in front of a contactor `K`.

    With `with_parent_device` the build also holds the parent's device `P` (150 A) on `B`'s other
    side, and both ends are external items: the unit's outside is in the build, so its boundary
    ports are no open ends. Without, the plant is the unit built alone: every item is in `u`, and
    its outside is not in the build, so `B`'s outward port (its first) and the boundary function
    `Bk` at `K`'s far end are open ends. `B`'s second port, the inner one that `K` hangs on, has
    the role `INTERNAL` (no open end) unless `inner_internal` is false: then it is open too.
    """
    plant = _dc_plant()
    unit = plant.unit("u")
    edge = device(plant, "B", rails=[["DC-"], ["DC+"]])
    if not with_parent_device and inner_internal:
        with_role(plant, edge[1], PortRole.INTERNAL)
    boundary = plant.boundary(unit, Plant.function_id("B", "f"))
    values = Operating(max_current_dc_a=Decimal(186))
    key = ("bv",)
    plant.add(
        BoundaryValuesFacet(
            id=make_id(BoundaryValuesFacet, key), key=key, subject=boundary, operating=values
        )
    )
    if with_parent_device:
        run(plant, edge[1], [contactor(plant, "K", k_amps)], external(plant, "T1"))
        run(plant, edge[0], [device(plant, "P", amps="150")], external(plant, "T0"))
    else:
        run(plant, edge[1], [contactor(plant, "K", k_amps)], hub(plant, "Bk"))
        plant.boundary(unit, Plant.function_id("Bk", "f"), key="bk")
        in_unit(plant, unit)
    return plant


def test_a_units_boundary_limit_bounds_a_parent_device_through_the_boundary() -> None:
    plant = _unit_string(with_parent_device=True, k_amps="200")
    finding = _the_finding(plant)
    assert finding.subjects == (Plant.function_id("P", "f"),)
    assert finding.message.endswith("set by the source of function 'f' of item B")


def test_the_units_standalone_build_finds_only_what_lies_inside_the_unit() -> None:
    """The unit alone: `B`'s outward port and `Bk` are open ends, so the loop through the outside
    passes `B` and `K` inside the unit is checked against `B`'s limit: 150 A fires, 200 A passes.
    No parent device, so nothing outside the unit is compared."""
    assert _fired(_unit_string(with_parent_device=False, k_amps="150")) == _ids("K")
    assert check_ratings_current(_unit_string(with_parent_device=False, k_amps="200").model()) == ()


def test_a_boundary_function_with_two_open_ports_leaves_the_string_beyond_it_unbounded() -> None:
    """If `B`'s inner port is open too (role `GENERIC`), the outside feeds `K` at that port
    without passing `B`: no limit lies on every loop through `K`, so no finding at 150 A. The
    twin with the `INTERNAL` inner port fires (the test above)."""
    plant = _unit_string(with_parent_device=False, k_amps="150", inner_internal=False)
    assert check_ratings_current(plant.model()) == ()


# -- acceptance 5: silence -----------------------------------------------------------------------


def test_no_bound_gives_no_finding() -> None:
    """A partial fuse bounds nothing and there is no source (the outside is one, but it sets no
    limit): the contactor is unchecked, though the string is open at both ends."""
    plant = _dc_plant()
    line = [fuse(plant, "F", "400", partial=True), contactor(plant, "K", "50")]
    node = hub(plant, "N")
    wire(plant, node, external(plant, "T0"))
    run(plant, node, line, external(plant, "T1"))
    plant.net("dc", (make_id(Port, ("F", "f", "1")),), potential="DC+")
    assert check_ratings_current(plant.model()) == ()


def test_a_device_with_no_current_rating_gives_no_finding() -> None:
    plant = _dc_plant()
    open_string(plant, _source(plant), [contactor(plant, "K", None)])
    assert check_ratings_current(plant.model()) == ()


def test_a_string_ending_at_a_real_dead_end_has_no_loop_and_gives_no_finding() -> None:
    """The same 150 A contactor on the 186 A string fires when the string is open (the twin,
    `_string`) and is silent when the far end is a dead end: no loop, so no bound."""
    plant = _dc_plant()
    run(plant, _source(plant)[1], [contactor(plant, "K", "150")], None)
    assert check_ratings_current(plant.model()) == ()
    assert _fired(_string("150")) == _ids("K")


def _kind_plant(*, ac_supply: bool) -> Plant:
    """A source limited to 100 A AC and a device rated 50 A AC, on an AC or a DC rail."""
    plant = Plant()
    current, name = (Current.AC, "L1") if ac_supply else (Current.DC, "DC+")
    supply(plant, "s", {name: rail("230", 0 if ac_supply else None)}, current=current)
    source = device(plant, "S", limit_ac="100", rails=[[], [name]])
    line = [device(plant, "D", amps="500", amps_ac="50", link=LinkKind.CONDUCTIVE)]
    open_string(plant, source, line)
    return plant


def test_an_ac_bound_on_a_device_that_reaches_only_dc_rails_gives_no_finding() -> None:
    assert check_ratings_current(_kind_plant(ac_supply=False).model()) == ()
    finding = _the_finding(_kind_plant(ac_supply=True))
    assert "rated 50 A AC" in finding.message
    assert "below its branch's 100 A AC" in finding.message


def test_a_model_with_no_supply_gives_no_finding() -> None:
    plant = Plant()
    run(plant, device(plant, "S", limit="186")[1], [contactor(plant, "K", "150")], None)
    assert check_ratings_current(plant.model()) == ()


# -- one finding per function, kind and source; order ----------------------------------------------


def test_two_rating_sources_of_one_function_each_fire_and_are_named() -> None:
    plant = _string("150")
    unit = plant.unit("u")
    boundary = plant.boundary(unit, Plant.function_id("K", "f"))
    plant.add(
        BoundaryValuesFacet(
            id=make_id(BoundaryValuesFacet, ("kb",)),
            key=("kb",),
            subject=boundary,
            rating=Rating(current_dc_a=Decimal(120)),
        )
    )
    found = check_ratings_current(plant.model())
    assert [f.message.split(", below")[0] for f in found] == [
        "function 'f' of item K is rated 120 A DC (boundary rating of unit u)",
        "function 'f' of item K is rated 150 A DC (part or template rating)",
    ]


def test_a_function_in_two_positions_is_checked_once_against_the_larger_bound() -> None:
    """A two-pin plug rated 150 A: pin 1 is bounded at 186 A, pin 2 at 100 A. One finding, 186."""
    plant = _dc_plant()
    part = rate(plant, "plug", "150")
    plug_function = plant.function(plant.item("plug", part=part), "f", kind=FunctionKind.CONNECTOR)
    socket_function = plant.function(plant.item("sock"), "f", kind=FunctionKind.CONNECTOR)
    plugs = [plant.port(plug_function, pin) for pin in ("1", "2")]
    socks = [plant.port(socket_function, pin) for pin in ("1", "2")]
    plant.mate(plug_function, socket_function)
    first, second = _source(plant, "S1", "186"), _source(plant, "S2", "300")
    wire(plant, first[0], external(plant, "Ta"))
    wire(plant, second[0], external(plant, "Tb"))
    run(plant, first[1], [], plugs[0])
    run(plant, second[1], [fuse(plant, "F", "100")], plugs[1])
    for index, pin in enumerate(socks):
        run(plant, pin, [device(plant, f"Z{index}", amps="300")], external(plant, f"Tz{index}"))
    finding = _the_finding(plant)
    assert finding.subjects == (plug_function,)
    assert (
        "below its branch's 186 A DC set by the source of function 'f' of item S1"
        in finding.message
    )


def test_findings_come_back_sorted_by_code_subjects_message() -> None:
    found = check_ratings_current(_two_strings_then_a_main_fuse().model())
    assert len(found) == 5
    assert list(found) == sorted(found, key=lambda f: (f.code, f.subjects, f.message))


# -- acceptance 3f: the outside ----------------------------------------------------------------


def _poles(plant: Plant) -> tuple:
    """`K1 - F1 - S - F2 - K2`: `K1` rated 160 A, `K2` 200 A, the fuses 400 A, `S` limited to
    186 A with DC- towards `K1`. Returns the free ends: `K1`'s first and `K2`'s last port."""
    k1, f1 = contactor(plant, "K1", "160"), fuse(plant, "F1")
    source = _source(plant)
    f2, k2 = fuse(plant, "F2"), contactor(plant, "K2", "200")
    run(plant, k1[1], [f1], source[0])
    run(plant, source[1], [f2], k2[0])
    return k1[0], k2[1]


def test_a_string_open_at_an_external_items_two_terminals_is_checked_against_its_source() -> None:
    plant = _dc_plant()
    plus, minus = _poles(plant)
    wire(plant, plus, external(plant, "Tp"))
    wire(plant, minus, external(plant, "Tm"))
    finding = _the_finding(plant)
    assert finding.subjects == (Plant.function_id("K1", "f"),)
    assert "rated 160 A DC" in finding.message
    assert "below its branch's 186 A DC set by the source of function 'f' of item S" in (
        finding.message
    )


def _string_unit(*, stray: bool) -> Plant:
    """The same string built alone: its two ends are boundary functions of the standalone unit
    `u`; with `stray` an item outside the unit makes it not standalone."""
    plant = _dc_plant()
    plus, minus = _poles(plant)
    unit = plant.unit("u")
    for tag, end in (("Bp", plus), ("Bm", minus)):
        wire(plant, end, hub(plant, tag))
        plant.boundary(unit, Plant.function_id(tag, "f"), key=tag)
    in_unit(plant, unit)
    if stray:
        plant.item("stray")
    return plant


def test_the_same_string_built_alone_is_checked_against_its_source() -> None:
    plant = _string_unit(stray=False)
    assert _fired(plant) == _ids("K1")
    assert _the_finding(plant).message.endswith("set by the source of function 'f' of item S")


def test_a_string_in_a_unit_that_is_not_standalone_is_not_open_at_its_boundary() -> None:
    """The unit's outside is in the build (it is not standalone): no open end, no loop, silence."""
    assert check_ratings_current(_string_unit(stray=True).model()) == ()


def test_a_load_across_both_poles_is_not_bounded_by_the_string() -> None:
    """A 20 A load `L` across the poles: the outside can feed it, no limit lies on every loop
    through it, so it gives no finding; `K1` keeps its 186 A."""
    plant = _dc_plant()
    plus, minus = _poles(plant)
    wire(plant, plus, external(plant, "Tp"))
    wire(plant, minus, external(plant, "Tm"))
    load = device(plant, "L", amps="20")
    wire(plant, plus, load[0])
    wire(plant, minus, load[1])
    assert _fired(plant) == _ids("K1")


def _two_open_ends(*, with_t1: bool) -> Plant:
    """The string, `-` open at `T3`; `+ - D - T2` with `D` rated 160 A, and with `with_t1` a
    second way out `+ - T1` (an unrated terminal of an external item)."""
    plant = _dc_plant()
    plus, minus = _poles(plant)
    wire(plant, minus, external(plant, "T3"))
    run(plant, plus, [contactor(plant, "D", "160")], external(plant, "T2"))
    if with_t1:
        wire(plant, plus, external(plant, "T1"))
    return plant


def test_a_device_on_a_second_way_out_of_the_pole_gives_no_finding() -> None:
    """With `T1`, the loop `T2 - D - + - T1` holds the outside and never passes the string's
    limit: `D` has no bound and no finding. A device inside the string still fires (`K1`)."""
    assert _fired(_two_open_ends(with_t1=True)) == _ids("K1")


def test_the_twin_without_the_second_way_out_bounds_the_device_in_series() -> None:
    """No `T1`: `D` is in series with the string on the only loop, bound 186 A, and fires."""
    assert _fired(_two_open_ends(with_t1=False)) == _ids("K1", "D")


# -- a link from a port to another function; switched links ------------------------------------


def test_a_source_with_a_sense_pin_still_bounds_the_string() -> None:
    """`T0 - S(supply, 186 A) - K(200 A) - F2(400 A) - T1`, `S`'s part has a function `m` whose
    pin is linked to `S`'s first port. The one loop is bounded 186 A by `S`, so `K` (200 A) gives
    no finding. When such a link dropped `S`, `K` got 400 A by `F2` and fired."""
    plant = _dc_plant()
    source = device(plant, "S", limit="186", kind=FunctionKind.SUPPLY, rails=[["DC-"], ["DC+"]])
    sense_pin(plant, "S")
    wire(plant, source[0], external(plant, "T0"))
    line = [contactor(plant, "K", "200"), fuse(plant, "F2")]
    run(plant, source[1], line, external(plant, "T1"))
    assert check_ratings_current(plant.model()) == ()


def _changeover_plant(d_amps: str, *, rated: bool = True, unrelated: bool = False) -> Plant:
    """Acceptance 3i: `M` (100 A) on a changeover's make throw, `E` (120 A) on its break throw,
    the common through a 400 A full-range fuse `F` to `D`, all ends at external items.

    The changeover `CO` is rated 500 A, or with `rated` false unrated (its links are wires).
    With `unrelated` a second unrated changeover `U` has its common on `D`'s far end: in the same
    component, but nothing that `D`'s bound depends on.
    """
    plant = _dc_plant()
    common, make, brk = changeover(plant, "CO", "500" if rated else None)
    for tag, throw in (("M", make), ("E", brk)):
        source = _source(plant, tag, "100" if tag == "M" else "120")
        wire(plant, source[0], external(plant, f"T{tag}"))
        wire(plant, source[1], throw)
    line = [fuse(plant, "F", "400"), device(plant, "D", amps=d_amps)]
    end = external(plant, "Td")
    run(plant, common, line, end)
    if unrelated:
        wire(plant, changeover(plant, "U", None)[0], end)
    return plant


def test_a_device_above_both_throws_bounds_gives_no_finding() -> None:
    """Acceptance 3i: with one throw closed at a time `D` is bounded by 100 A (operated) or
    120 A (at rest), and 200 A is above both. Counting both throws closed gave it 400 A."""
    assert check_ratings_current(_changeover_plant("200").model()) == ()


def test_a_device_below_a_throws_bound_fires_with_the_state_named() -> None:
    """`D` at 110 A is below the 120 A of the rest state only: one finding, naming the state."""
    finding = _the_finding(_changeover_plant("110"))
    assert finding.subjects == (Plant.function_id("D", "f"),)
    assert finding.message == (
        "function 'f' of item D is rated 110 A DC (part or template rating), "
        "below its branch's 120 A DC set by the source of function 'f' of item E, "
        "with item CO at rest"
    )


def test_a_device_below_both_bounds_reports_the_highest_of_the_states() -> None:
    """`D` at 90 A fires in both states (100 A operated, 120 A at rest): the bound reported is
    the highest, 120 A, at rest."""
    finding = _the_finding(_changeover_plant("90"))
    assert finding.message.endswith(
        "below its branch's 120 A DC set by the source of function 'f' "
        "of item E, with item CO at rest"
    )


_D_110 = (
    "function 'f' of item D is rated 110 A DC (part or template rating), "
    "below its branch's 120 A DC set by the source of function 'f' of item E, "
    "with item CO at rest"
)


def test_an_unrated_changeover_gives_the_same_findings() -> None:
    """The changeover's links are plain wires, and `link_state` still closes one throw at a time."""
    assert check_ratings_current(_changeover_plant("200", rated=False).model()) == ()
    assert _the_finding(_changeover_plant("110", rated=False)).message == _D_110


def test_the_message_names_only_the_item_that_matters() -> None:
    """`U` is in `D`'s component and is enumerated, but `D`'s 120 A holds whatever it does."""
    assert _the_finding(_changeover_plant("110", unrelated=True)).message == _D_110


@pytest.mark.parametrize("above_the_cap", [False, True])
def test_a_capped_unrated_changeover_does_not_raise_the_bound(*, above_the_cap: bool) -> None:
    """The unrated changeover `CO`, enumerated or above the cap, has `L` (100 A) on every loop
    through `D`: a 150 A `D` is fine, a 90 A one fires at 100 A by `L`. Opening all of `CO`'s
    links when it is above the cap gave `D` 400 A by `S` and a false finding for the 150 A."""
    cap = current_states.MAX_ENUMERATED_ITEMS
    others = cap if above_the_cap else cap - 1

    def plant(d_amps: str) -> Plant:
        built = _dc_plant()
        capped_changeover(built, others, _source(built, "S", "400"), d_amps)
        return built

    assert check_ratings_current(plant("150").model()) == ()
    assert _the_finding(plant("90")).message == (
        "function 'f' of item D is rated 90 A DC (part or template rating), "
        "below its branch's 100 A DC set by the protective device of function 'f' of item L"
    )


def test_a_position_shorted_by_a_link_closed_in_the_other_state_is_still_checked() -> None:
    """`T0 - S(186 A) - CO.common`, `D` (100 A) from the common to the make port: at rest `D`
    is on the loop with `S`, operated and with every link closed it is shorted. It fires at rest."""
    plant = _dc_plant()
    shorted_when_closed(plant, _source(plant, "S", "186"))
    assert _the_finding(plant).message == (
        "function 'f' of item D is rated 100 A DC (part or template rating), "
        "below its branch's 186 A DC set by the source of function 'f' of item S, "
        "with item CO at rest"
    )


def test_the_check_is_an_error_run_once_by_all_validators() -> None:
    model = _string("150").model()
    once = [
        f for check in ALL_VALIDATORS for f in check(model) if f.code == RATING_CURRENT_BELOW_BRANCH
    ]
    assert len(once) == 1
    assert once[0].severity is Severity.ERROR
    assert ALL_VALIDATORS.index(check_ratings_current) == ALL_VALIDATORS.index(check_ratings) + 1
    assert check_supplies in ALL_VALIDATORS
