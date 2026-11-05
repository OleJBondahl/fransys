"""A bundle is the nets that connect the poles of one multi-pole device: one trunk, one lane a pole.

Three-phase feeds from a 3-pole breaker are the shape. A crossed feed is a bundle whose
crossed end carries the permutation; a ragged feed is in none.
"""

from itertools import pairwise
from typing import cast
lazy from collections.abc import Callable

import fransys as fr
import pytest
from fransys.colours import BU
from plant import Plant

from fransys_model.derive.bundles import Bundle, bundle_of, bundles
from fransys_model.vocab.tables import functions, items, ports
lazy from fransys_model.kernel import Id
lazy from fransys_model.vocab import Function, Port

_MCB = "DEMO-MCB-3P"
_MOTOR = "DEMO-MOTOR-4KW"
_WIRE = (BU, 2.5)
_PHASES = (("2", "U"), ("4", "V"), ("6", "W"))


def _port(model: fr.Model, tag: str, name: str) -> Id[Port]:
    """The port `name` of the item whose last key part is `tag`."""
    (found,) = [p.id for p in ports(model).values() if p.name == name and items(model)[functions(model)[p.function].item].key[-1] == tag]
    return found


def _feed() -> fr.Design:
    """Q1's load side to three motors by direct wires, M1 to M2 to M3 on every phase."""
    d = fr.design("demo_parts")
    q = d.device("Q1", _MCB)
    motors = [d.device(f"M{n}", _MOTOR) for n in (1, 2, 3)]
    for load, pin in _PHASES:
        d.series(q.element[load], motors[0][pin], wire=_WIRE)
        for near, far in pairwise(motors):
            d.series(near[pin], far[pin], wire=_WIRE)
    return d


@pytest.fixture(scope="module")
def feed() -> fr.Model:
    """The three-phase feed model."""
    return fr.build(_feed()).model


def _lane(model: fr.Model, tag: str, name: str) -> tuple[Id[Port], int]:
    found = bundle_of(model, _port(model, tag, name))
    assert found is not None, f"{tag}:{name} is in no bundle"
    return found[:2]


def test_a_three_phase_feed_is_one_bundle_in_phase_order(feed: fr.Model) -> None:
    """Catches a bundle split by motor or by phase, or poles out of L1 L2 L3 order."""
    load = _lane(feed, "Q1", "2")[0]
    (bundle,) = [b for b in bundles(feed) if b.id == load]
    assert isinstance(bundle, Bundle)
    assert [n.pole for n in bundle.nets] == [0, 1, 2]
    for tag in ("Q1", "M1", "M2", "M3"):
        for (load_pin, motor_pin), pole in zip(_PHASES, range(3), strict=True):
            pin = load_pin if tag == "Q1" else motor_pin
            assert _lane(feed, tag, pin) == (load, pole)


def test_a_net_that_is_no_phase_is_in_no_bundle(feed: fr.Model) -> None:
    """Catches a PE net, or a port of no net, handed a lane (the phases above are in one)."""
    assert bundle_of(feed, _port(feed, "M1", "PE")) is None
    assert _lane(feed, "M1", "U")[1] == 0


def test_the_line_side_of_the_breaker_is_its_own_bundle(feed: fr.Model) -> None:
    """The breaker alone makes its line side a bundle (poles 0 to 2), apart from its load side."""
    line = {_lane(feed, "Q1", pin) for pin in ("1", "3", "5")}
    assert {pole for _, pole in line} == {0, 1, 2}
    assert len({bundle for bundle, _ in line}) == 1
    assert line.isdisjoint({_lane(feed, "Q1", pin) for pin in ("2", "4", "6")})


def test_a_feed_through_in_line_terminals_stays_one_trunk() -> None:
    """The closure joins a terminal's two sides, so Q1 -> X2 -> M1 is one bundle, not three."""
    d = fr.design("demo_parts")
    q, m = d.device("Q1", _MCB), d.device("M1", _MOTOR)
    x = d.terminal_strip("X2", "DEMO-TB-2.5-TWIN")
    for number, (load, pin) in enumerate(_PHASES, 1):
        d.series(q.element[load], x[number].inner, wire=_WIRE)
        d.series(x[number].inner, m[pin], wire=_WIRE)
    model = fr.build(d).model
    (trunk,) = {_lane(model, "Q1", load)[0] for load, _ in _PHASES}
    assert [_lane(model, "M1", pin) for _, pin in _PHASES] == [(trunk, n) for n in range(3)]


def _two_breakers(order: tuple[tuple[str, str], ...]) -> fr.Model:
    """Q1's load pins wired to Q2's line pins as `order` says."""
    d = fr.design("demo_parts")
    q1, q2 = d.device("Q1", _MCB), d.device("Q2", _MCB)
    for load, line in order:
        d.series(q1.element[load], q2.element[line], wire=_WIRE)
    return fr.build(d).model


def test_crossed_phases_between_two_breakers_are_a_bundle_with_a_permutation() -> None:
    """Catches a crossed net left out, or the reversal lost; the straight feed carries no cross."""
    straight = _two_breakers((("2", "1"), ("4", "3"), ("6", "5")))
    assert [_lane(straight, "Q2", pin)[1] for pin in ("1", "3", "5")] == [0, 1, 2]
    crossed = _two_breakers((("2", "5"), ("4", "3"), ("6", "1")))  # the reversing swap
    lanes = {_lane(crossed, t, p) for t, p in (("Q1", "2"), ("Q1", "4"), ("Q1", "6"))}
    assert {pole for _, pole in lanes} == {0, 1, 2}
    assert {_lane(crossed, "Q2", pin) for pin in ("1", "3", "5")} == lanes
    assert len([b for b in bundles(crossed) if b.id == next(iter(lanes))[0]]) == 1


def test_a_trunk_with_two_nets_on_one_pole_is_in_no_bundle() -> None:
    """Catches a bundle with a repeated pole index (a staircase of breakers: pole 0, 1, 0)."""
    d = fr.design("demo_parts")
    q = [d.device(f"Q{n}", _MCB) for n in (1, 2, 3, 4)]
    for a, pin_a, b, pin_b in ((0, "2", 1, "1"), (1, "3", 2, "4"), (2, "2", 3, "1")):
        d.series(q[a].element[pin_a], q[b].element[pin_b], wire=_WIRE)
    model = fr.build(d).model
    assert bundle_of(model, _port(model, "Q1", "2")) is None
    assert _lane(model, "Q1", "1")[1] == 0  # a breaker's untouched side is a bundle still


def test_the_wired_poles_of_a_half_wired_trunk_are_the_bundle() -> None:
    """Catches unwired poles that repeat a pole index and sink the trunk (poles 0 and 1 wired)."""
    model = _two_breakers((("2", "1"), ("4", "3")))
    wired = {_lane(model, "Q1", "2"), _lane(model, "Q1", "4")}
    assert wired == {_lane(model, "Q2", "1"), _lane(model, "Q2", "3")}
    assert {pole for _, pole in wired} == {0, 1}
    assert len({bundle for bundle, _ in wired}) == 1
    (bundle,) = [b for b in bundles(model) if b.id == _lane(model, "Q1", "2")[0]]
    assert len(bundle.nets) == 2  # the unwired pole 2 is not a member
    assert bundle_of(model, _port(model, "Q1", "6")) is None


def test_one_wired_pole_is_no_bundle() -> None:
    """Catches a lone wired pole bundled with the unwired poles beside it."""
    d = fr.design("demo_parts")
    q = d.device("Q1", _MCB)
    x = d.terminal_strip("X2", "DEMO-TB-2.5")
    d.series(q.element["4"], x[1].inner, wire=_WIRE)
    model = fr.build(d).model
    assert bundle_of(model, _port(model, "Q1", "4")) is None
    assert bundle_of(model, _port(model, "Q1", "2")) is None


def test_nets_that_part_partway_are_one_bundle_over_the_span_they_share() -> None:
    """Q1 feeds M1 on two phases and M2 on the third: one bundle at Q1, poles 0, 1, 2."""
    d = fr.design("demo_parts")
    q = d.device("Q1", _MCB)
    m1, m2 = d.device("M1", _MOTOR), d.device("M2", _MOTOR)
    d.series(q.element["2"], m1["U"], wire=_WIRE)
    d.series(q.element["4"], m1["V"], wire=_WIRE)
    d.series(q.element["6"], m2["W"], wire=_WIRE)
    model = fr.build(d).model
    lanes = [_lane(model, "Q1", pin) for pin in ("2", "4", "6")]
    assert [pole for _, pole in lanes] == [0, 1, 2]
    assert len({bundle for bundle, _ in lanes}) == 1
    assert _lane(model, "M2", "W") == lanes[2]


def test_a_function_with_no_declared_pole_link_forms_no_pole_bundle() -> None:
    """A 4-pin connector declares no pole link: its pins pair no poles, so nets from pins 1 and 3 do not bundle."""
    d = fr.design("demo_parts")
    a, b = d.device("J1", "DEMO-CONN-4P"), d.device("J2", "DEMO-CONN-4P")
    d.series(a[1], b[1], wire=_WIRE)
    d.series(a[3], b[3], wire=_WIRE)
    model = fr.build(d).model
    assert bundle_of(model, _port(model, "J1", "1")) is None
    assert bundle_of(model, _port(model, "J1", "3")) is None
    assert not [b for b in bundles(model) if b.form == "pole"]


def _cabled(*, second_cable_shares_a_net: bool) -> fr.Model:
    """W1 carries two cores from J1 to J2; W2 optionally leaves J1 pin 1 again (a common net) with a second core."""
    d = fr.design("demo_parts")
    j1, j2, j3 = (d.device(tag, "DEMO-HSG-4F", contacts="DEMO-CRIMP-F") for tag in ("J1", "J2", "J3"))
    w1 = d.cable("W1", "DEMO-CBL-4G1.5", length_m=1)
    w1.core(1, j1[1], j2[1])
    w1.core(2, j1[2], j2[2])
    if second_cable_shares_a_net:
        w2 = d.cable("W2", "DEMO-CBL-4G1.5", length_m=1)
        w2.core(1, j1[1], j3[1])
        w2.core(2, j1[3], j3[3])
    return fr.build(d).model


def test_a_cables_cores_are_one_line_bundle_in_core_order() -> None:
    """Catches a cable left as separate wires, lanes out of core order, or a cable bundle that answers as a pole one."""
    model = _cabled(second_cable_shares_a_net=False)
    (cable,) = [b for b in bundles(model) if b.form == "line"]
    assert (cable.form, [lane.pole for lane in cable.nets]) == ("line", [0, 1])
    port = _port(model, "J1", "1")
    assert (bundle_of(model, port) or (cable.id, 0, "pole"))[2] == "pole"
    assert bundle_of(model, port, ("line",)) == (cable.id, 0, "line")


def test_a_net_is_in_one_trunk_so_a_cable_sharing_a_net_with_an_earlier_one_stays_wires() -> None:
    """Catches two cables given one bundle id (their shared net), which the layout would fan together."""
    cables = [b for b in bundles(_cabled(second_cable_shares_a_net=True)) if b.form == "line"]
    assert len(cables) == 1


def test_cores_are_laid_out_by_core_index_then_id() -> None:
    """Catches a lane order by id alone, which the id salt would shuffle."""
    from fransys_model.derive.order import cores_in_lane_order

    a, b, c = (Id(kind="conductor", value=v) for v in ("c", "a", "b"))
    assert cores_in_lane_order({a: 1, b: 2, c: 2}, [c, b, a]) == [a, b, c]


def _crossed_poles() -> dict[tuple[str, str], int]:
    """The pole of each pin of a crossed pair of breakers, built in the current id namespace."""
    model = _two_breakers((("2", "5"), ("4", "3"), ("6", "1")))
    return {(t, p): _lane(model, t, p)[1] for t, pins in (("Q1", "246"), ("Q2", "135")) for p in pins}


def test_a_crossed_bundle_takes_its_poles_from_the_same_end_at_every_salt() -> None:
    """Catches a source end picked by id hash: the poles would swap ends between salts."""
    from fransys_model.kernel import id_namespace

    def under(salt: str) -> dict[tuple[str, str], int]:
        with id_namespace(salt):
            return _crossed_poles()

    runs = [under(salt) for salt in "abcde"]
    assert runs[0] == {("Q1", "2"): 0, ("Q1", "4"): 1, ("Q1", "6"): 2, ("Q2", "5"): 0, ("Q2", "3"): 1, ("Q2", "1"): 2}
    assert all(run == runs[0] for run in runs)


def test_functions_stand_in_designation_name_order_at_every_salt() -> None:
    """Catches a function order read from the Id hash: it would differ between salts (model-0396)."""
    from fransys_model.derive.order import function_order_text, functions_in_order
    from fransys_model.kernel import id_namespace

    def under(salt: str) -> list[tuple[str, str]]:
        with id_namespace(salt):
            d = fr.design("demo_parts")
            d.device("K1", "DEMO-RLY-2CO-24")
            d.device("K2", "DEMO-RLY-2CO-24")
            model = fr.build(d).model
            return [
                (function_order_text(model, cast("Id[Function]", f)), functions(model)[cast("Id[Function]", f)].name)
                for f in functions_in_order(model, functions(model))
            ]

    runs = [under(salt) for salt in "abcde"]
    assert runs[0] == sorted(runs[0], key=lambda t: t[0].split(" ")[0])
    assert all(run == runs[0] for run in runs)


def _keys_at_every_salt(
    make: Callable[[], tuple[list[tuple[str, ...]], list[tuple[str, ...]]]],
) -> list[tuple[list[tuple[str, ...]], list[tuple[str, ...]]]]:
    """`make()` under each id salt: (authoring keys in the order under test, authoring keys in Id order)."""
    from fransys_model.kernel import id_namespace

    def under(salt: str) -> tuple[list[tuple[str, ...]], list[tuple[str, ...]]]:
        with id_namespace(salt):
            return make()

    return [under(salt) for salt in "abcde"]


def _tied_order_holds_the_authoring_key(make: Callable[[], tuple[list[tuple[str, ...]], list[tuple[str, ...]]]]) -> None:
    """The tied records stand in authoring-key order at every salt, and Id order differs at one (so the test can fail)."""
    runs = _keys_at_every_salt(make)
    assert all(ordered == sorted(ordered) for ordered, _ in runs)
    assert any(by_id != ordered for ordered, by_id in runs)


_TIED = [f"k{n}" for n in range(8, 0, -1)]


def test_units_of_one_designation_stand_in_authoring_key_order_at_every_salt() -> None:
    """Catches a unit order broken by the Id hash (KI-384): the sets would follow the id seed."""
    from fransys_model.derive.order import units_in_order
    from fransys_model.vocab.tables import units

    def make() -> tuple[list[tuple[str, ...]], list[tuple[str, ...]]]:
        plant = Plant()
        for key in _TIED:
            plant.unit(key, tag="U1")
        model = plant.model()
        return [units(model)[u].key for u in units_in_order(model, units(model))], [u.key for u in units(model).values()]

    _tied_order_holds_the_authoring_key(make)


def test_items_of_one_designation_stand_in_authoring_key_order_at_every_salt() -> None:
    """Catches an item order broken by the Id hash (KI-384): the strips would follow the id seed."""
    from fransys_model.derive.order import in_designation_order

    def make() -> tuple[list[tuple[str, ...]], list[tuple[str, ...]]]:
        plant = Plant()
        for key in _TIED:
            plant.item(key, designation="K1")
        model = plant.model()
        return [items(model)[i].key for i in in_designation_order(model, items(model))], [i.key for i in items(model).values()]

    _tied_order_holds_the_authoring_key(make)


def test_locations_of_one_label_stand_in_authoring_key_order_at_every_salt() -> None:
    """Catches a location order broken by the Id hash (KI-384): the root's sets would follow the id seed."""
    from fransys_model.derive.order import locations_in_order
    from fransys_model.kernel import Draft, Origin, freeze, make_id
    from fransys_model.vocab.aspects import AspectNode
    from fransys_model.vocab.enums import Aspect
    from fransys_model.vocab.tables import aspect_nodes

    def make() -> tuple[list[tuple[str, ...]], list[tuple[str, ...]]]:
        draft = Draft()
        nodes = [AspectNode(id=make_id(AspectNode, (k,)), key=(k,), aspect=Aspect.LOCATION, parent=None, label="C1", description="") for k in _TIED]
        draft.extend(nodes, origin=Origin(file="test", line=1, note="fixture"))
        model = freeze(draft)
        return [aspect_nodes(model)[n].key for n in locations_in_order(model, aspect_nodes(model))], [n.key for n in aspect_nodes(model).values()]

    _tied_order_holds_the_authoring_key(make)


def test_channels_of_one_number_and_name_stand_in_authoring_key_order_at_every_salt() -> None:
    """Catches a channel tie broken by the Id hash (KI-384): two modules' channels would swap with the seed."""
    from fransys_model.derive.order import plc_channel_tie

    def make() -> tuple[list[tuple[str, ...]], list[tuple[str, ...]]]:
        plant = Plant()
        for key in _TIED:
            plant.function(plant.item(key), "di_1")
        found = list(functions(plant.model()).values())
        return [f.key for f in sorted(found, key=lambda f: plc_channel_tie(1, f))], [f.key for f in sorted(found, key=lambda f: f.id)]

    _tied_order_holds_the_authoring_key(make)


def test_harness_blocks_of_one_reading_stand_in_authoring_key_order_at_every_salt() -> None:
    """Catches a block order broken by the Id hash (KI-384): the harness list would follow the id seed."""
    from fransys_model.derive.order import blocks_in_print_order

    def make() -> tuple[list[tuple[str, ...]], list[tuple[str, ...]]]:
        plant = Plant()
        pairs = [(None, plant.item(key)) for key in _TIED]
        model = plant.model()
        ordered = blocks_in_print_order(model, pairs, cabled=set(pairs))
        return [items(model)[s].key for _, s in ordered], [items(model)[s].key for _, s in sorted(pairs, key=lambda p: p[1])]

    _tied_order_holds_the_authoring_key(make)


def test_a_relay_lists_its_coil_before_its_contacts_though_the_names_sort_the_other_way() -> None:
    """Catches the contact rank dropped from the function order: `co_1` sorts before `coil` by name alone."""
    from fransys_model.derive.order import functions_in_order

    d = fr.design("demo_parts")
    d.device("K1", "DEMO-RLY-2CO-24")
    model = fr.build(d).model
    names = [functions(model)[cast("Id[Function]", f)].name for f in functions_in_order(model, functions(model))]
    assert sorted(names) == ["co_1", "co_2", "coil"]
    assert names == ["coil", "co_1", "co_2"]
