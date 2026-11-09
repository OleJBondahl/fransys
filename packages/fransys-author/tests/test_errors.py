"""Every `AuthorError` case: a failing test and a passing twin."""

from decimal import Decimal
from typing import Any

import pytest
from fransys_author import AuthorError
from fransys_author.design import Design

from fransys_model.kernel import make_id
from fransys_model.vocab import Revision, UnitRelease, UnusedBoundary


def test_unknown_mpn_names_the_closest_matches(parts):
    d = Design(parts)
    with pytest.raises(AuthorError, match=r"TEST-RLY-2C0.*closest.*TEST-RLY-2CO"):
        d.item("TEST-RLY-2C0", tag="K1")


def test_a_known_mpn_is_not_an_error(parts):
    d = Design(parts)
    d.item("TEST-RLY-2CO", tag="K1")


def test_unknown_mpn_with_no_close_match_names_none(parts):
    d = Design(parts)
    with pytest.raises(AuthorError, match=r"in the loaded libraries$"):
        d.item("zzz-nothing-alike-000000", tag="K1")


def test_unknown_manufacturer_mpn_pair(parts):
    d = Design(parts)
    with pytest.raises(AuthorError, match=r"TEST-RLY-2CO.*Gamma"):
        d.item(("Gamma", "TEST-RLY-2CO"), tag="K1")


def test_a_known_manufacturer_mpn_pair_is_not_an_error(parts):
    d = Design(parts)
    d.item(("TestCo", "TEST-RLY-2CO"), tag="K1")


def test_ambiguous_mpn_asks_for_the_manufacturer_tuple(parts):
    d = Design(parts)
    with pytest.raises(AuthorError, match=r"ambiguous.*Alpha.*Beta"):
        d.item("TEST-SHARED", tag="A1")


def test_the_manufacturer_tuple_disambiguates_the_same_mpn(parts):
    d = Design(parts)
    d.item(("Alpha", "TEST-SHARED"), tag="A1")


def test_a_part_with_no_cable_product_facet_is_not_a_cable(parts):
    d = Design(parts)
    with pytest.raises(AuthorError, match="cable_product"):
        d.cable("TEST-RLY-2CO", tag="W1")


def test_a_part_with_a_cable_product_facet_is_a_cable(parts):
    d = Design(parts)
    d.cable("TEST-CBL-2", tag="W1")


def test_unknown_marking_on_a_function_lists_its_markings(parts):
    d = Design(parts)
    k1 = d.item("TEST-RLY-2CO", tag="K1")
    with pytest.raises(AuthorError, match=r"A9.*A1.*A2"):
        _ = k1.fn("coil")["A9"]


def test_a_known_marking_on_a_function_is_not_an_error(parts):
    d = Design(parts)
    k1 = d.item("TEST-RLY-2CO", tag="K1")
    assert k1.fn("coil")["A1"].name == "A1"


def test_unknown_marking_on_an_item_lists_its_markings(parts):
    d = Design(parts)
    k1 = d.item("TEST-RLY-2CO", tag="K1")
    with pytest.raises(AuthorError, match="marked 'ZZ'"):
        _ = k1["ZZ"]


def test_a_known_marking_on_an_item_is_not_an_error(parts):
    d = Design(parts)
    k1 = d.item("TEST-RLY-2CO", tag="K1")
    assert k1["A1"].name == "A1"


def test_ambiguous_marking_on_an_item_names_the_fn_workaround(parts):
    d = Design(parts)
    a1 = d.item("TEST-CLASH", tag="A1")
    with pytest.raises(AuthorError, match=r"item\.fn\(\"<function name>\"\)\['13'\]"):
        _ = a1["13"]


def test_unknown_function_name_lists_the_item_s_functions(parts):
    d = Design(parts)
    k1 = d.item("TEST-RLY-2CO", tag="K1")
    with pytest.raises(AuthorError, match=r"co_2.*coil.*no_1"):
        k1.fn("nope")


def test_a_known_function_name_is_not_an_error(parts):
    d = Design(parts)
    k1 = d.item("TEST-RLY-2CO", tag="K1")
    assert k1.fn("coil").name == "coil"


def test_a_terminal_with_no_external_port_has_no_outer(parts):
    d = Design(parts)
    x1 = d.strip("X1")
    t1 = x1.terminal("TEST-TB-ONE-SIDED")
    with pytest.raises(AuthorError, match="external"):
        _ = t1.outer


def test_a_terminal_with_an_internal_port_has_an_inner(parts):
    d = Design(parts)
    x1 = d.strip("X1")
    t1 = x1.terminal("TEST-TB-ONE-SIDED")
    assert t1.inner.boundary.value == "internal"


def test_core_index_out_of_range(parts):
    d = Design(parts)
    x1 = d.strip("X1")
    t1, t2 = x1.terminal("TEST-TB"), x1.terminal("TEST-TB")
    w1 = d.cable("TEST-CBL-2", tag="W1")
    with pytest.raises(AuthorError, match="out of range"):
        w1.core(3, t1.outer, t2.outer)


def test_a_core_index_within_range_is_not_an_error(parts):
    d = Design(parts)
    x1 = d.strip("X1")
    t1, t2 = x1.terminal("TEST-TB"), x1.terminal("TEST-TB")
    w1 = d.cable("TEST-CBL-2", tag="W1")
    w1.core(2, t1.outer, t2.outer)


def test_a_float_gauge_is_refused(parts):
    d = Design(parts)
    bad_gauge: Any = 0.75  # deliberately the wrong type, to reach the runtime guard
    with pytest.raises(AuthorError, match="float"):
        d.wiring(colour="BU", gauge=bad_gauge)


def test_a_str_or_decimal_gauge_is_accepted(parts):

    d = Design(parts)
    d.wiring(colour="BU", gauge="0.75")
    d.wiring(colour="BU", gauge=Decimal("0.75"))


def test_a_float_gauge_override_on_a_call_is_also_refused(parts):
    d = Design(parts)
    x1 = d.strip("X1")
    t1, t2 = x1.terminal("TEST-TB"), x1.terminal("TEST-TB")
    wire = d.wiring(colour="BU", gauge="0.75")
    bad_gauge: Any = 1.5
    with pytest.raises(AuthorError, match="float"):
        wire(t1.inner, t2.inner, gauge=bad_gauge)


def test_neither_name_nor_tag_is_an_error(parts):
    d = Design(parts)
    with pytest.raises(AuthorError, match=r"name=.*tag="):
        d.item("TEST-RLY-2CO")


def test_name_alone_is_not_an_error(parts):
    d = Design(parts)
    d.item("TEST-RLY-2CO", name="run")


def test_wire_run_needs_at_least_two_points(parts):
    d = Design(parts)
    x1 = d.strip("X1")
    t1 = x1.terminal("TEST-TB")
    wire = d.wiring(colour="BU", gauge="0.75")
    with pytest.raises(AuthorError, match="at least 2"):
        wire.run(t1.inner)


def test_wire_run_with_two_points_is_not_an_error(parts):
    d = Design(parts)
    x1 = d.strip("X1")
    t1, t2 = x1.terminal("TEST-TB"), x1.terminal("TEST-TB")
    wire = d.wiring(colour="BU", gauge="0.75")
    wire.run(t1.inner, t2.inner)


def test_order_needs_at_least_two_groups(parts):
    d = Design(parts)
    g1 = d.group("G1")
    with pytest.raises(AuthorError, match="at least 2"):
        d.order(g1)


def test_order_with_two_groups_is_not_an_error(parts):
    d = Design(parts)
    g1, g2 = d.group("G1"), d.group("G2")
    d.order(g1, g2)


def test_bridge_needs_at_least_two_terminals(parts):
    d = Design(parts)
    x1 = d.strip("X1")
    t1 = x1.terminal("TEST-TB")
    with pytest.raises(AuthorError, match="at least 2"):
        d.bridge(t1)


def test_bridge_with_two_terminals_is_not_an_error(parts):
    d = Design(parts)
    x1 = d.strip("X1")
    t1, t2 = x1.terminal("TEST-TB"), x1.terminal("TEST-TB")
    d.bridge(t1, t2)


def test_bridge_of_terminals_on_two_strips_names_the_terminals_and_their_strips(parts):
    d = Design(parts)
    x1 = d.strip("X1")
    x2 = d.strip("X2")
    t1 = x1.terminal("TEST-TB")
    t2 = x2.terminal("TEST-TB")
    with pytest.raises(AuthorError, match=r"one strip.*X1.*X2"):
        d.bridge(t1, t2)


def test_bridge_with_a_terminal_given_twice_is_refused(parts):
    d = Design(parts)
    x1 = d.strip("X1")
    t1, t2 = x1.terminal("TEST-TB"), x1.terminal("TEST-TB")
    with pytest.raises(AuthorError, match="given twice"):
        d.bridge(t1, t2, t1)


def test_bridging_the_same_pair_twice_from_one_scope_is_a_no_op(parts):
    """The jumper's key is its pair's two terminal keys, so re-bridging the same
    pair with identical content is the existing duplicate-key no-op, not a second record."""
    from fransys_model.vocab.connectivity import Conductor

    d = Design(parts)
    x1 = d.strip("X1")
    t1, t2 = x1.terminal("TEST-TB"), x1.terminal("TEST-TB")
    d.bridge(t1, t2)
    d.bridge(t1, t2)
    conductors = [r for r in d.draft().records() if isinstance(r, Conductor)]
    assert len(conductors) == 1


def test_reauthoring_a_name_with_different_content_is_refused(parts):
    d = Design(parts)
    d.item("TEST-RLY-2CO", tag="K1")
    with pytest.raises(AuthorError, match="already names a different"):
        d.item("TEST-CONN-2P", tag="K1")


def test_an_item_of_a_terminal_part_is_refused_and_the_fix_names_the_strip(parts):
    """R2102: a terminal is authored only on a strip, so `d.item` of a terminal-category part raises."""
    # UNDO: author/_scope_build.py item: drop the TERMINAL function-template check: FAILED here
    with pytest.raises(AuthorError, match=r"authored only on a strip; use d\.terminal_strip"):
        Design(parts).item("TEST-TB", tag="X1")


def test_adding_an_item_key_twice_is_refused_naming_both_calls(parts):
    d = Design(parts)
    d.item("TEST-RLY-2CO", tag="K1")
    with pytest.raises(AuthorError, match=r"'K1' was already added.*test_errors.py:\d+.*keep the handle from the first call"):
        d.item("TEST-RLY-2CO", tag="K1")


def test_a_strip_called_twice_is_refused(parts):
    d = Design(parts)
    d.strip("X1")
    with pytest.raises(AuthorError, match="keep the handle from the first call"):
        d.strip("X1")


def test_reauthoring_the_identical_call_is_a_no_op(parts):
    d = Design(parts)
    a = d.location("C1", "cabinet")
    b = d.location("C1", "cabinet")
    assert a.id == b.id
    assert len(d.draft().records()) == 1


def test_an_unrecognised_net_class_lists_the_valid_ones(parts):
    d = Design(parts)
    x1 = d.strip("X1")
    t1, t2 = x1.terminal("TEST-TB"), x1.terminal("TEST-TB")
    with pytest.raises(AuthorError, match=r"power.*control.*signal"):
        d.net("N1", t1.outer, t2.outer, cls="nonsense")


def test_a_known_net_class_is_not_an_error(parts):
    d = Design(parts)
    x1 = d.strip("X1")
    t1, t2 = x1.terminal("TEST-TB"), x1.terminal("TEST-TB")
    d.net("N1", t1.outer, t2.outer, cls="power")


def test_an_unrecognised_signal_type_lists_the_valid_ones(parts):
    d = Design(parts)
    k1 = d.item("TEST-RLY-2CO", tag="K1")
    with pytest.raises(AuthorError, match=r"di.*do"):
        k1.fn("coil").plc("nonsense", "SIG")


def test_a_float_scale_bound_is_refused(parts):
    d = Design(parts)
    k1 = d.item("TEST-RLY-2CO", tag="K1")
    bad_eng: Any = (0.0, 10.0)
    with pytest.raises(AuthorError, match="float"):
        k1.fn("coil").scale("m", raw=(0, 100), eng=bad_eng)


def test_str_or_decimal_scale_bounds_are_accepted(parts):
    d = Design(parts)
    k1 = d.item("TEST-RLY-2CO", tag="K1")
    k1.fn("coil").scale("m", raw=(0, 100), eng=("0", Decimal(10)))


def test_a_second_scale_on_one_channel_says_to_call_it_once(parts):
    d = Design(parts)
    k1 = d.item("TEST-RLY-2CO", tag="K1")
    k1.fn("coil").scale("m", raw=(0, 100), eng=("0", "10"))
    with pytest.raises(AuthorError, match=r"Call \.scale once per channel"):
        k1.fn("coil").scale("m", raw=(0, 100), eng=("0", "20"))


def test_a_known_signal_type_is_not_an_error(parts):
    d = Design(parts)
    k1 = d.item("TEST-RLY-2CO", tag="K1")
    k1.fn("coil").plc("do", "SIG")


def test_harness_without_a_tag_is_a_type_error(parts):
    """`tag` is required, keyword-only (decision author-0003): a
    part-less harness gets no class letter from numbering, so an untagged one would never
    gain a designation. `name=` alone used to be enough (the old signature's `tag` had a
    default, so a real call giving only `name=` -- the case the ruling is about -- built a
    """
    d = Design(parts)
    harness: Any = d.harness
    with pytest.raises(TypeError, match="tag"):
        harness(name="w1", at=d.location("C1", "cabinet"))


def test_profile_with_an_unknown_number_and_no_other_is_refused(parts):
    d = Design(parts)
    with pytest.raises(AuthorError, match="does not have wobble_factor"):
        d.profile(wobble_factor=9)


def test_boundary_on_a_scope_with_no_unit_is_refused(parts):
    d = Design(parts)
    x1 = d.item("TEST-CONN-2P", tag="X1")
    with pytest.raises(AuthorError, match="needs a unit"):
        d.boundary(x1)


def test_boundary_on_a_scope_with_a_unit_is_not_an_error(parts):
    d = Design(parts)
    u = d.scope("u1").unit("demo-unit", revision=1, interface="1")
    x1 = u.item("TEST-CONN-2P", tag="X1")
    u.boundary(x1)


def test_boundary_of_an_ambiguous_target_is_refused(parts):
    d = Design(parts)
    u = d.scope("u1").unit("demo-unit", revision=1, interface="1")
    k1 = u.item("TEST-RLY-2CO", tag="K1")  # three functions: coil, no_1, co_2
    with pytest.raises(AuthorError, match="exactly one"):
        u.boundary(k1)


def test_an_item_with_several_functions_names_them_as_candidates(parts):
    d = Design(parts)
    u = d.scope("u1").unit("demo-unit", revision=1, interface="1")
    k1 = u.item("TEST-RLY-2CO", tag="K1")
    with pytest.raises(AuthorError) as caught:
        k1.as_function()
    handles = str(caught.value).split("name one of ")[1]
    assert handles == ", ".join(f"k1.{name}" for name in sorted(f.name for f in k1.functions))
    assert len(k1.functions) == 3


def test_boundary_of_an_unambiguous_target_is_not_an_error(parts):
    d = Design(parts)
    u = d.scope("u1").unit("demo-unit", revision=1, interface="1")
    k1 = u.item("TEST-RLY-2CO", tag="K1")
    u.boundary(k1.fn("coil"))


def test_unit_called_twice_on_one_prefix_is_refused(parts):
    d = Design(parts)
    s = d.scope("u1")
    s.unit("demo-unit", revision=1, interface="1")
    with pytest.raises(AuthorError, match=r"already has a unit \('demo-unit'\)"):
        s.unit("demo-unit", revision=1, interface="1")


def test_unit_called_once_on_a_prefix_is_not_an_error(parts):
    d = Design(parts)
    d.scope("u1").unit("demo-unit", revision=1, interface="1")


def test_unused_needs_no_unit(parts):
    d = Design(parts)
    x1 = d.item("TEST-CONN-2P", tag="X1")
    d.unused(x1)
    (record,) = [r for r in d.draft().records() if isinstance(r, UnusedBoundary)]
    assert record.function == x1.as_function().id


def test_unused_from_a_nested_scope_prefixes_the_key(parts):
    d = Design(parts)
    u = d.scope("p1")
    x1 = u.item("TEST-CONN-2P", tag="X1")
    u.unused(x1)
    (record,) = [r for r in d.draft().records() if isinstance(r, UnusedBoundary)]
    assert record.key[0] == "p1"


def test_unused_of_an_ambiguous_target_is_refused(parts):
    d = Design(parts)
    k1 = d.item("TEST-RLY-2CO", tag="K1")  # three functions: coil, no_1, co_2
    with pytest.raises(AuthorError, match="exactly one"):
        d.unused(k1)


def test_revision_on_a_scope_with_a_unit_writes_the_expected_record(parts):
    d = Design(parts)
    u = d.scope("cab").unit("demo-unit", revision=1, interface="1")
    u.revision(1, date="2026-09-23", text="First release", created="OJB", checked="KN")
    (record,) = [r for r in d.draft().records() if isinstance(r, Revision)]
    assert record.release == make_id(UnitRelease, ("unit_release", "demo-unit", "1", "1"))
    assert record.version == 1
    assert record.key == ("unit_release", "demo-unit", "1", "1", "revision", "1", "1")
    assert record.revision == 1
    assert record.date == "2026-09-23"
    assert record.text == "First release"
    assert record.created == "OJB"
    assert record.checked == "KN"
    assert record.approved == ""


def test_revision_on_a_scope_with_no_unit_is_refused(parts):
    d = Design(parts)
    s = d.scope("cab")
    with pytest.raises(AuthorError, match="needs a unit"):
        s.revision(1, date="2026-09-23", text="x", created="OJB")


def test_design_revision_writes_with_unit_none_even_though_design_has_no_unit(parts):
    """The discriminating test: `Design._unit` is also `None`, like a plain unit-less
    `Scope`, but `Design.revision` is special-cased to write anyway (unit=None is the
    project's own history), never raising `s.revision()`'s own guard."""
    d = Design(parts)
    assert d.unit_id is None
    d.revision(1, date="2026-09-23", text="First issue", created="OJB")
    (record,) = [r for r in d.draft().records() if isinstance(r, Revision)]
    assert record.release is None
    assert record.key == ("revision", "1", "1")


def test_scope_unit_id_round_trips_through_unit(parts):
    s = Design(parts).scope("cab")
    assert s.unit_id is None
    u = s.unit("demo-unit", revision=1, interface="1")
    assert u.unit_id is not None
    assert u.unit_id == u.unit_id  # stable across reads


def test_a_units_revision_key_does_not_collide_with_the_projects_own(parts):
    """A unit's own revision key (amended 2026-09-23) is
    `(*prefix, "unit", <unit name>, "revision", revision)`, not the project's own flat
    `(*prefix, "revision", revision)` -- so a unit made directly off `Design` and the
    project's own history never collide, even on the identical revision string. (Before
    """
    d = Design(parts)
    u = d.unit("demo-unit", revision=1, interface="1")
    u.revision(1, date="2026-09-23", text="unit rev", created="OJB")
    d.revision(1, date="2026-09-23", text="project rev", created="OJB")
    revisions = [r for r in d.draft().records() if isinstance(r, Revision)]
    assert len(revisions) == 2
    unit_record = next(r for r in revisions if r.release is not None)
    project_record = next(r for r in revisions if r.release is None)
    assert unit_record.key != project_record.key
    assert unit_record.key == ("unit_release", "demo-unit", "1", "1", "revision", "1", "1")
    assert project_record.key == ("revision", "1", "1")


def test_profile_with_an_unknown_number_is_refused(parts):

    d = Design(parts)
    with pytest.raises(AuthorError, match="does not have"):
        d.profile(wobble_factor=9)
