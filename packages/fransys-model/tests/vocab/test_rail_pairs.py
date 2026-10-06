"""CONTACT-STATES CS4 tests: `rail_pairs`, the rails that can stand across a function at once.

A rail reaches a port under conditions, the state each contact item on its way must be in: a
`rest` link needs its item at rest, an `operated` link needs it operated, `both` links, conductors
and mates need nothing. One item is at rest or operated as a whole (CS1). Every plant here is
hand-built and invented: two rails `A` and `B` of one AC supply and a load with two ports.

Can-fail probes, each one Edit in `vocab/closure.py`, run and undone: `_agree` returning `True`
fails the no-pair tests (a), (b) and the missing second route (d); `_spread` never rejecting an
inconsistent condition fails the (e) drop test; a condition on every port of a changeover (a fake
shared item in a state per rail) fails the open-gap test; dropping the antichain pruning
(`other <= grown` to `other == grown`, no displacement) fails the pruning test and (d).
"""

from typing import TYPE_CHECKING, NamedTuple

import pytest
from plant import Plant
from rating_plant import rail, rated, supply

from fransys_model.kernel import make_id
from fransys_model.vocab import PartRatingFacet, closure, rail_pairs
from fransys_model.vocab.core import Function
from fransys_model.vocab.enums import FunctionKind, LinkKind, PartCategory, PortRole
from fransys_model.vocab.tables import items
from fransys_model.vocab.templates import FunctionTemplate, Part, PortTemplate
from fransys_model.vocab.validators.ratings import check_ratings

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Port

_GENERIC = PortRole.GENERIC
_PROPER_ROLES = (PortRole.COMMON, PortRole.BREAK, PortRole.MAKE)
_AB = frozenset({("A", "B")})
# A pole: function name, kind, its (pin, role) pairs, its (from pin, to pin) switched links.
type _Pole = tuple[str, FunctionKind, tuple[tuple[str, PortRole], ...], tuple[tuple[str, str], ...]]
_NO: _Pole = ("no", FunctionKind.CONTACT_NO, (("13", _GENERIC), ("14", _GENERIC)), (("13", "14"),))
_NC: _Pole = ("nc", FunctionKind.CONTACT_NC, (("21", _GENERIC), ("22", _GENERIC)), (("21", "22"),))


_DEFAULT_NAMES = ("11", "12", "14")


def _co(
    roles: tuple[PortRole, PortRole, PortRole],
    names: tuple[str, str, str] = _DEFAULT_NAMES,
) -> _Pole:
    """A changeover pole: pins `names` (11, 12, 14 by default) with `roles`, in that order; the
    first links to the second and to the third."""
    pins = tuple(zip(names, roles, strict=True))
    return ("co", FunctionKind.CONTACT_CO, pins, ((names[0], names[1]), (names[0], names[2])))


class _Relay:
    """One item of its own part: a function per pole, ports named `<pole>.<pin>` in `pins`."""

    def __init__(self, plant: Plant, key: str, poles: Sequence[_Pole]) -> None:
        part = Part(
            id=make_id(Part, (f"part-{key}",)),
            key=(f"part-{key}",),
            mpn="EXAMPLE-K",
            manufacturer="Example Co",
            description="Invented",
            category=PartCategory.ELECTROMECHANICAL,
            class_code="K",
        )
        plant.add(part)
        item = plant.item(key, part=part.id)
        self.functions: dict[str, Id[Function]] = {}
        self.pins: dict[str, Id[Port]] = {}
        for name, kind, pins, links in poles:
            template = FunctionTemplate(
                id=make_id(FunctionTemplate, (key, name)),
                key=(key, name),
                part=part.id,
                name=name,
                kind=kind,
            )
            plant.add(template)
            ends = {
                pin: PortTemplate(
                    id=make_id(PortTemplate, (key, name, pin)),
                    key=(key, name, pin),
                    function=template.id,
                    name=pin,
                    role=role,
                )
                for pin, role in pins
            }
            plant.add(*ends.values())
            for a, b in links:
                plant.link(ends[a], ends[b], LinkKind.SWITCHED, key=f"{key}-{name}-{a}-{b}")
            function = plant.function(item, name, template=template.id, kind=kind)
            self.functions[name] = function
            for pin, end in ends.items():
                self.pins[f"{name}.{pin}"] = plant.port(function, pin, template=end.id)


class _Load(NamedTuple):
    function: Id[Function]
    p0: Id[Port]
    p1: Id[Port]


def _plant() -> Plant:
    """A plant with the one AC supply, rails `A` and `B` (398 V across them)."""
    plant = Plant()
    supply(plant, "ac", {"A": rail("230", 0), "B": rail("230", 120)})
    return plant


def _load(plant: Plant, *, ac: str | None = None) -> _Load:
    """A load `load` with ports `p0` and `p1`; rated `ac` V AC when given."""
    part = None
    if ac is not None:
        part = plant.part("R")
        plant.add(
            PartRatingFacet(
                id=make_id(PartRatingFacet, ("load",)),
                key=("load",),
                subject=part,
                rating=rated(ac=ac),
            )
        )
    function = plant.function(plant.item("load", part=part), "f")
    return _Load(function, plant.port(function, "p0"), plant.port(function, "p1"))


def _no_nc(*, same_item: bool, ac: str | None = None) -> tuple[Model, _Load]:
    """A on the NO contact's input, B on the NC contact's input; both outputs and both load ports
    on one net. One relay item carries both contacts when `same_item`, else two relays do."""
    plant = _plant()
    if same_item:
        no = nc = _Relay(plant, "k1", (_NO, _NC))
    else:
        no, nc = _Relay(plant, "k1", (_NO,)), _Relay(plant, "k2", (_NC,))
    load = _load(plant, ac=ac)
    plant.net("A", (no.pins["no.13"],), potential="A")
    plant.net("B", (nc.pins["nc.21"],), potential="B")
    plant.wire(no.pins["no.14"], nc.pins["nc.22"], key="w-join")
    plant.wire(no.pins["no.14"], load.p0, key="w-p0")
    plant.wire(no.pins["no.14"], load.p1, key="w-p1")
    return plant.model(), load


def _changeover(
    roles: tuple[PortRole, PortRole, PortRole],
    names: tuple[str, str, str] = _DEFAULT_NAMES,
) -> tuple[Model, _Relay, _Load]:
    """A on the make end (third pin), B on the break end (second), the common (first) to both
    load ports."""
    common, brk, make = (f"co.{name}" for name in names)
    plant = _plant()
    relay = _Relay(plant, "k1", (_co(roles, names),))
    load = _load(plant)
    plant.net("A", (relay.pins[make],), potential="A")
    plant.net("B", (relay.pins[brk],), potential="B")
    plant.wire(relay.pins[common], load.p0, key="w-p0")
    plant.wire(relay.pins[common], load.p1, key="w-p1")
    return plant.model(), relay, load


def _protection() -> tuple[Model, _Load]:
    """A through a switched link of a protection function to `p0`; B declared on `p1`."""
    plant = _plant()
    guard = _Relay(
        plant,
        "f1",
        (("prot", FunctionKind.PROTECTION, (("1", _GENERIC), ("2", _GENERIC)), (("1", "2"),)),),
    )
    load = _load(plant)
    plant.net("A", (guard.pins["prot.1"],), potential="A")
    plant.wire(guard.pins["prot.2"], load.p0, key="w-p0")
    plant.net("B", (load.p1,), potential="B")
    return plant.model(), load


def _plain() -> tuple[Model, _Load]:
    """No stateful link at all: A wired to `p0`, B declared on `p1`."""
    plant = _plant()
    load = _load(plant)
    other = plant.pin("src", "f", "1")
    plant.net("A", (other,), potential="A")
    plant.wire(other, load.p0, key="w-p0")
    plant.net("B", (load.p1,), potential="B")
    return plant.model(), load


def _two_routes(*, second_route: bool) -> tuple[Model, _Load, dict[str, Id[Port]]]:
    """A reaches `p0` through K1's NO contact and, when `second_route`, K2's NC contact; B
    reaches `p1` through K1's NC contact. B needs K1 at rest, so only K2's route agrees."""
    plant = _plant()
    k1 = _Relay(plant, "k1", (_NO, _NC))
    load = _load(plant)
    a_inputs = (k1.pins["no.13"],)
    if second_route:
        k2 = _Relay(plant, "k2", (_NC,))
        a_inputs = (*a_inputs, k2.pins["nc.21"])
        plant.wire(k2.pins["nc.22"], load.p0, key="w-k2")
    plant.net("A", a_inputs, potential="A")
    plant.net("B", (k1.pins["nc.21"],), potential="B")
    plant.wire(k1.pins["no.14"], load.p0, key="w-k1")
    plant.wire(k1.pins["nc.22"], load.p1, key="w-b")
    return plant.model(), load, k1.pins


def _one_item_both_ways(*, same_item: bool) -> tuple[Model, _Load]:
    """A through a NO contact and then an NC contact to `p0`, B declared on `p1`."""
    plant = _plant()
    if same_item:
        first = second = _Relay(plant, "k1", (_NO, _NC))
    else:
        first, second = _Relay(plant, "k1", (_NO,)), _Relay(plant, "k2", (_NC,))
    load = _load(plant)
    plant.net("A", (first.pins["no.13"],), potential="A")
    plant.wire(first.pins["no.14"], second.pins["nc.21"], key="w-mid")
    plant.wire(second.pins["nc.22"], load.p0, key="w-p0")
    plant.net("B", (load.p1,), potential="B")
    return plant.model(), load


def _conditions(model: Model, port: Id[Port], rail_name: str) -> set[frozenset[tuple[str, str]]]:
    """The conditions of `rail_name` at `port`, an item shown by its key."""
    found = closure._rail_states(model).at_port[port][rail_name]
    return {frozenset((items(model)[item].key[0], state) for item, state in c) for c in found}


def test_a_no_and_an_nc_contact_of_one_item_do_not_pass_two_rails_to_one_load() -> None:
    """(a) The item is at rest or operated, never both: A and B never reach the load together."""
    model, load = _no_nc(same_item=True)
    assert rail_pairs(model, load.function) == frozenset()
    # (f) `port_rails` still counts every contact closed
    assert closure.port_rails(model, load.p0) == {"A", "B"}


def test_the_same_two_contacts_on_two_items_do_pass_both_rails_to_one_load() -> None:
    model, load = _no_nc(same_item=False)
    assert rail_pairs(model, load.function) == _AB
    assert closure.port_rails(model, load.p0) == {"A", "B"}


def test_a_load_behind_one_items_no_and_nc_is_checked_to_earth_not_across_the_rails() -> None:
    """230 V to earth passes a 250 V load; 398 V across two items' contacts does not."""
    same, _ = _no_nc(same_item=True, ac="250")
    assert check_ratings(same) == ()
    different, load = _no_nc(same_item=False, ac="250")
    (finding,) = check_ratings(different)
    assert finding.subjects == (load.function,)
    assert "rails 'A' and 'B' stand across it at 398.4 V" in finding.message


def test_a_changeover_never_stands_its_two_rails_across_a_load_it_feeds() -> None:
    """(b) The common closes to the make end or the break end, never both."""
    model, _, load = _changeover(_PROPER_ROLES)
    assert rail_pairs(model, load.function) == frozenset()


def test_a_changeovers_own_throw_ports_still_stand_across_its_open_gap() -> None:
    """(b) The make end on A and the break end on B stand across the pole: no link between."""
    model, relay, _ = _changeover(_PROPER_ROLES)
    assert rail_pairs(model, relay.functions["co"]) == _AB
    # (f) the common carries both, as before
    assert closure.port_rails(model, relay.pins["co.11"]) == {"A", "B"}


@pytest.mark.parametrize(
    "names",
    [("11", "12", "14"), ("COM", "NC", "NO"), ("I", "II", "III")],
    ids=["11-12-14", "COM-NC-NO", "I-II-III"],
)
def test_a_changeovers_rail_pairs_do_not_depend_on_how_its_pins_are_named(
    names: tuple[str, str, str],
) -> None:
    """Acceptance 4: the roles decide, not the pin names. Every naming scheme gives what `11/12/14`
    gives: no pair across the load, the open-gap pair at the pole; with no roles the load's pair."""
    default_model, default_relay, default_load = _changeover(_PROPER_ROLES)
    default_load_pairs = rail_pairs(default_model, default_load.function)
    default_pole_pairs = rail_pairs(default_model, default_relay.functions["co"])
    assert default_load_pairs == frozenset()
    assert default_pole_pairs == _AB

    model, relay, load = _changeover(_PROPER_ROLES, names)
    assert rail_pairs(model, load.function) == default_load_pairs == frozenset()
    assert rail_pairs(model, relay.functions["co"]) == default_pole_pairs == _AB

    generic = (_GENERIC, _GENERIC, _GENERIC)
    generic_model, _, generic_load = _changeover(generic, names)
    assert rail_pairs(generic_model, generic_load.function) == _AB


def test_a_generic_role_changeover_still_pairs_its_rails_across_the_load() -> None:
    """(c) With no roles the state is `both` and no condition is added, as today."""
    model, _, load = _changeover((_GENERIC, _GENERIC, _GENERIC))
    assert rail_pairs(model, load.function) == _AB


def test_a_switched_link_of_a_protection_function_adds_no_condition() -> None:
    """(c) A protection device is closed in both states: A across the load with B, as today."""
    model, load = _protection()
    assert rail_pairs(model, load.function) == _AB


def test_two_ways_to_a_port_keep_both_conditions_and_a_pair_is_found_through_either() -> None:
    """(d) A at `p0` needs K1 operated or K2 at rest; B at `p1` needs K1 at rest: K2's route."""
    model, load, pins = _two_routes(second_route=True)
    assert _conditions(model, load.p0, "A") == {
        frozenset({("k1", "operated")}),
        frozenset({("k2", "rest")}),
    }
    assert rail_pairs(model, load.function) == _AB
    assert closure.port_rails(model, load.p0) == {"A"}
    assert closure.port_rails(model, pins["nc.22"]) == {"B"}


def test_without_the_second_route_the_pair_is_gone() -> None:
    """(d) K1's NO route needs K1 operated and B needs it at rest."""
    model, load, _ = _two_routes(second_route=False)
    assert _conditions(model, load.p0, "A") == {frozenset({("k1", "operated")})}
    assert rail_pairs(model, load.function) == frozenset()
    assert closure.port_rails(model, load.p0) == {"A"}


def test_a_path_that_needs_one_item_in_both_states_is_dropped() -> None:
    """(e) A through K1's NO and then K1's NC reaches nothing, though `port_rails` says it does."""
    model, load = _one_item_both_ways(same_item=True)
    assert closure.port_rails(model, load.p0) == {"A"}
    assert "A" not in closure._rail_states(model).at_port.get(load.p0, {})
    assert rail_pairs(model, load.function) == frozenset()


def test_the_same_path_through_two_items_is_kept() -> None:
    """(e) NO of K1 then NC of K2 is a consistent condition: A reaches `p0`, and pairs with B."""
    model, load = _one_item_both_ways(same_item=False)
    assert _conditions(model, load.p0, "A") == {frozenset({("k1", "operated"), ("k2", "rest")})}
    assert rail_pairs(model, load.function) == _AB


def test_only_the_minimal_conditions_at_a_port_are_kept() -> None:
    """A reaches `p0` by K1's NO contact, and again through it and J's NC contact: the second is
    no new way there, its condition contains the first, and so at J's output."""
    plant = _plant()
    k1, j = _Relay(plant, "k1", (_NO,)), _Relay(plant, "j", (_NC,))
    load = _load(plant)
    plant.net("A", (k1.pins["no.13"],), potential="A")
    plant.wire(k1.pins["no.14"], load.p0, key="w-direct")
    plant.wire(k1.pins["no.14"], j.pins["nc.21"], key="w-into-j")
    plant.wire(j.pins["nc.22"], load.p0, key="w-out-of-j")
    plant.net("B", (load.p1,), potential="B")
    model = plant.model()
    assert _conditions(model, load.p0, "A") == {frozenset({("k1", "operated")})}
    assert _conditions(model, j.pins["nc.22"], "A") == {frozenset({("k1", "operated")})}
    assert rail_pairs(model, load.function) == _AB


def test_a_function_with_no_pair_no_rail_or_no_record_gives_the_empty_set() -> None:
    model, load = _plain()
    assert rail_pairs(model, load.function) == _AB
    unloaded = _plant()
    bare = _load(unloaded)
    assert rail_pairs(unloaded.model(), bare.function) == frozenset()
    assert rail_pairs(model, make_id(Function, ("absent",))) == frozenset()


@pytest.mark.parametrize(
    "build",
    [
        pytest.param(
            lambda: _changeover((_GENERIC, _GENERIC, _GENERIC))[0], id="generic-changeover"
        ),
        pytest.param(lambda: _protection()[0], id="protection"),
        pytest.param(lambda: _plain()[0], id="plain"),
    ],
)
def test_with_no_stateful_link_the_conditional_table_reaches_exactly_what_port_rails_does(
    build: Callable[[], Model],
) -> None:
    """(g) Every link `both` or conductive: no condition, no path dropped."""
    model = build()
    table = {port: frozenset(rails) for port, rails in closure._rail_states(model).at_port.items()}
    assert table
    assert table == dict(closure._rails(model))


def test_the_stateful_plants_reach_a_subset_of_what_port_rails_does() -> None:
    """A link only adds a condition and never blocks: every (port, rail) here is in `port_rails`."""
    for model in (
        _no_nc(same_item=True)[0],
        _changeover(_PROPER_ROLES)[0],
        _one_item_both_ways(same_item=True)[0],
        _two_routes(second_route=True)[0],
    ):
        for port, rails in closure._rail_states(model).at_port.items():
            assert set(rails) <= closure.port_rails(model, port)
