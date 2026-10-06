"""CONTACT-STATES acceptance 3: a brute-force oracle for `derive.rail_pairs`.

The oracle knows nothing of conditions. For every rest-or-operated assignment of the items that
hold stateful links it builds the model with only the links that assignment closes, asks
`port_rails` for the rails of each port, and pairs two different rails at two different ports of
one function. The union of those pairs over all assignments must equal `rail_pairs` on the model
that has every contact link (spec CS1, CS2, CS4).

A generated `_Spec` is plain data (items as tuples of pole kinds, attachments of a rail to a
port, wires between two ports); `_build` turns it into a model. Invented data only.
"""

import itertools
from dataclasses import dataclass
from functools import cache
from typing import TYPE_CHECKING

from examples import bundle_records
from hypothesis import Phase, find, given, settings
from hypothesis import strategies as st
from plant import Plant
from rating_plant import rail, supply

from fransys_model.derive import port_rails, rail_pairs
from fransys_model.kernel import Origin, evolve, make_id
from fransys_model.vocab.core import Function, Port
from fransys_model.vocab.enums import FunctionKind, LinkKind, PartCategory, PortRole
from fransys_model.vocab.instantiate import PartBundle, instantiate
from fransys_model.vocab.templates import FunctionTemplate, InternalLink, Part, PortTemplate

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from fransys_model.kernel import Id, Model

_STATEFUL = ("no", "nc", "co")
_PLAIN = ("fuse", "terminal", "load")
_RAILS = ("a1", "a2", "b1", "b2")
_TWO = ("1", "2")
_CO = (
    ("com", PortRole.COMMON),
    ("brk", PortRole.BREAK),
    ("mk", PortRole.MAKE),
)
_KIND = {
    "no": FunctionKind.CONTACT_NO,
    "nc": FunctionKind.CONTACT_NC,
    "co": FunctionKind.CONTACT_CO,
    "fuse": FunctionKind.PROTECTION,
    "terminal": FunctionKind.GENERIC,
    "load": FunctionKind.GENERIC,
}

type _Pole = str
type _Item = tuple[_Pole, ...]
type _Assignment = Mapping[int, str]


@dataclass(frozen=True, slots=True)
class _Spec:
    """Items (each a tuple of pole kinds), rails put on ports, wires between ports.

    `attachments` and `wires` name a port by its index in `_ports(spec)`.
    """

    items: tuple[_Item, ...]
    attachments: tuple[tuple[int, str], ...]
    wires: tuple[tuple[int, int], ...]


def _port_names(pole: _Pole) -> tuple[str, ...]:
    return tuple(name for name, _ in _CO) if pole == "co" else _TWO


def _ports(spec: _Spec) -> tuple[tuple[int, int, str], ...]:
    """Every port of the spec as (item, pole, name), in a stable order."""
    return tuple(
        (item, index, name)
        for item, poles in enumerate(spec.items)
        for index, pole in enumerate(poles)
        for name in _port_names(pole)
    )


def _function_id(item: int, index: int) -> Id[Function]:
    return make_id(Function, (f"i{item}", "fn", f"p{index}"))


def _port_id(port: tuple[int, int, str]) -> Id[Port]:
    item, index, name = port
    return make_id(Port, (f"i{item}", "fn", f"p{index}", "port", name))


def _functions(spec: _Spec) -> tuple[tuple[int, int], ...]:
    return tuple(
        (item, index) for item, poles in enumerate(spec.items) for index in range(len(poles))
    )


def _links_closed(pole: _Pole, state: str | None) -> tuple[tuple[str, str], ...]:
    """The internal links (a, b) of a pole that stay when its item is in `state`.

    `None` keeps every link: the model `rail_pairs` reads.
    """
    if pole == "no":
        return (("1", "2"),) if state in (None, "operated") else ()
    if pole == "nc":
        return (("1", "2"),) if state in (None, "rest") else ()
    if pole == "co":
        kept = []
        if state in (None, "rest"):
            kept.append(("com", "brk"))
        if state in (None, "operated"):
            kept.append(("com", "mk"))
        return tuple(kept)
    if pole == "load":
        return ()
    return (("1", "2"),)


@cache
def _bundle(poles: _Item, state: str | None) -> PartBundle:
    """A part of one function per pole; only the links closed in `state` are on it."""
    part_key = ("oracle", "-".join(poles), state or "all")
    part = Part(
        id=make_id(Part, part_key),
        key=part_key,
        mpn="ORACLE-1",
        manufacturer="Example Co",
        description="Invented",
        category=PartCategory.ELECTROMECHANICAL,
        class_code="K",
    )
    functions: list[FunctionTemplate] = []
    ports: list[PortTemplate] = []
    links: list[InternalLink] = []
    for index, pole in enumerate(poles):
        function_key = (*part_key, "fn", f"p{index}")
        functions.append(
            FunctionTemplate(
                id=make_id(FunctionTemplate, function_key),
                key=function_key,
                part=part.id,
                name=f"p{index}",
                kind=_KIND[pole],
            )
        )
        roles = dict(_CO) if pole == "co" else {}
        by_name: dict[str, PortTemplate] = {}
        for name in _port_names(pole):
            port_key = (*function_key, "port", name)
            by_name[name] = PortTemplate(
                id=make_id(PortTemplate, port_key),
                key=port_key,
                function=functions[-1].id,
                name=name,
                role=roles.get(name, PortRole.GENERIC),
            )
        ports.extend(by_name.values())
        kind = LinkKind.CONDUCTIVE if pole == "terminal" else LinkKind.SWITCHED
        for a, b in _links_closed(pole, state):
            link_key = (*function_key, "link", a, b)
            links.append(
                InternalLink(
                    id=make_id(InternalLink, link_key),
                    key=link_key,
                    a=by_name[a].id,
                    b=by_name[b].id,
                    kind=kind,
                )
            )
    return PartBundle(
        part=part,
        function_templates=tuple(functions),
        port_templates=tuple(ports),
        internal_links=tuple(links),
    )


def _stateful_items(spec: _Spec) -> tuple[int, ...]:
    return tuple(
        item for item, poles in enumerate(spec.items) if any(pole in _STATEFUL for pole in poles)
    )


def _build_from(spec: _Spec, bundle_of: Callable[[int, _Item], PartBundle]) -> Model:
    """Every item's `bundle_of(item, poles)` wired per `spec`; the one plant both builders use."""
    plant = Plant()
    supply(plant, "s1", {"a1": rail("230", 0), "a2": rail("230", 120)})
    supply(plant, "s2", {"b1": rail("230", 0), "b2": rail("230", 120)})
    added: set[Id[Part]] = set()
    for item, poles in enumerate(spec.items):
        bundle = bundle_of(item, poles)
        if bundle.part.id not in added:
            added.add(bundle.part.id)
            plant.add(*bundle_records(bundle))
        plant.add(*instantiate(bundle, (f"i{item}",)))
    ports = tuple(_port_id(port) for port in _ports(spec))
    for index, (port, name) in enumerate(spec.attachments):
        plant.net(f"n{index}", (ports[port],), potential=name)
    for index, (a, b) in enumerate(spec.wires):
        plant.wire(ports[a], ports[b], key=f"w{index}")
    return plant.model()


def _build(spec: _Spec, assignment: _Assignment | None = None) -> Model:
    """The model of `spec`; `None` keeps every contact link, else drops the links open in it.

    A link that is closed stays, and `port_rails` then counts it closed. Kept as a fresh
    `freeze()` per call (unlike `_brute_force`'s evolve path below) so the small fixed-spec
    tests cross-check the construction route `_brute_force` no longer takes.
    """
    return _build_from(
        spec,
        lambda item, poles: _bundle(poles, None if assignment is None else assignment.get(item)),
    )


@cache
def _item_bundle(
    item: int, poles: _Item
) -> tuple[PartBundle, dict[tuple[int, str, str], InternalLink]]:
    """A zero-links part unique to this item, and every internal link it could hold.

    Not `_bundle`'s part, shared by every item with the same `poles`: an internal link lives
    on the part template, not the instance, and `_brute_force` may put a different state on
    two items of the same `poles` within one assignment, so they must not share a template
    (a shared one would close the same link for both).
    """
    part_key = ("oracle", f"i{item}", "-".join(poles), "zero")
    part = Part(
        id=make_id(Part, part_key),
        key=part_key,
        mpn="ORACLE-1",
        manufacturer="Example Co",
        description="Invented",
        category=PartCategory.ELECTROMECHANICAL,
        class_code="K",
    )
    functions: list[FunctionTemplate] = []
    ports: list[PortTemplate] = []
    by_pair: dict[tuple[int, str, str], InternalLink] = {}
    for index, pole in enumerate(poles):
        function_key = (*part_key, "fn", f"p{index}")
        functions.append(
            FunctionTemplate(
                id=make_id(FunctionTemplate, function_key),
                key=function_key,
                part=part.id,
                name=f"p{index}",
                kind=_KIND[pole],
            )
        )
        roles = dict(_CO) if pole == "co" else {}
        by_name: dict[str, PortTemplate] = {}
        for name in _port_names(pole):
            port_key = (*function_key, "port", name)
            by_name[name] = PortTemplate(
                id=make_id(PortTemplate, port_key),
                key=port_key,
                function=functions[-1].id,
                name=name,
                role=roles.get(name, PortRole.GENERIC),
            )
        ports.extend(by_name.values())
        kind = LinkKind.CONDUCTIVE if pole == "terminal" else LinkKind.SWITCHED
        for a, b in _links_closed(pole, None):
            link_key = (*function_key, "link", a, b)
            by_pair[(index, a, b)] = InternalLink(
                id=make_id(InternalLink, link_key),
                key=link_key,
                a=by_name[a].id,
                b=by_name[b].id,
                kind=kind,
            )
    bundle = PartBundle(
        part=part,
        function_templates=tuple(functions),
        port_templates=tuple(ports),
        internal_links=(),
    )
    return bundle, by_pair


def _closed_links(spec: _Spec, assignment: _Assignment) -> tuple[InternalLink, ...]:
    """Every internal link closed under `assignment` (`None` for an item it does not name)."""
    closed = []
    for item, poles in enumerate(spec.items):
        state = assignment.get(item)
        _, by_pair = _item_bundle(item, poles)
        for index, pole in enumerate(poles):
            closed.extend(by_pair[(index, a, b)] for a, b in _links_closed(pole, state))
    return tuple(closed)


_ORACLE_ORIGIN = Origin(file=__file__, line=0, note="rail-pairs oracle: one brute-force state")


def _standing(model: Model, spec: _Spec) -> dict[tuple[int, int], set[tuple[str, str]]]:
    """Per function, the pairs of two rails at two different ports, by `port_rails` alone."""
    result: dict[tuple[int, int], set[tuple[str, str]]] = {}
    for item, index in _functions(spec):
        named = [
            port_rails(model, _port_id(port)) for port in _ports(spec) if port[:2] == (item, index)
        ]
        pairs = result.setdefault((item, index), set())
        for first, second in itertools.combinations(named, 2):
            pairs.update(
                (min(one, other), max(one, other))
                for one in first
                for other in second
                if one != other
            )
    return result


def _brute_force(spec: _Spec) -> dict[tuple[int, int], set[tuple[str, str]]]:
    """The union of `_standing` over every rest-or-operated assignment of the stateful items.

    Builds the zero-links model once (`_build_zero`) and, for each assignment, puts back
    exactly the links it closes (`_closed_links`) instead of freezing a fresh model: `evolve`
    only checks and hashes the records it puts, where a fresh `freeze()` re-checks every
    record in the model (SPEED-RAIL-PAIRS Part 0 found that the slow part).
    """
    stateful = _stateful_items(spec)
    union: dict[tuple[int, int], set[tuple[str, str]]] = {key: set() for key in _functions(spec)}
    base = _build_zero(spec)
    for states in itertools.product(("rest", "operated"), repeat=len(stateful)):
        assignment = dict(zip(stateful, states, strict=True))
        put = _closed_links(spec, assignment)
        model = evolve(base, put=put, origin=_ORACLE_ORIGIN)
        for key, pairs in _standing(model, spec).items():
            union[key] |= pairs
    return union


def _build_zero(spec: _Spec) -> Model:
    """Every item's bundle with no internal link at all: `_brute_force`'s evolve base."""
    return _build_from(spec, lambda item, poles: _item_bundle(item, poles)[0])


def _all_closed(spec: _Spec) -> dict[tuple[int, int], set[tuple[str, str]]]:
    """The pairs of `port_rails` on the every-link model, with no state told apart."""
    return _standing(_build(spec), spec)


def _reads(spec: _Spec) -> dict[tuple[int, int], frozenset[tuple[str, str]]]:
    """`rail_pairs` of every function of the every-link model."""
    model = _build(spec)
    return {key: rail_pairs(model, _function_id(*key)) for key in _functions(spec)}


@st.composite
def _specs(draw: st.DrawFn) -> _Spec:
    """At most six items with stateful poles, up to three plain ones, wired at random.

    Six is 64 models per example; the spec's bound of eight is one fixed example below.
    """
    size = draw(st.sampled_from((1, 2, 2, 3, 3, 3, 4, 4, 5, 6)))
    # Freezing a model costs by its record count, so most items are one pole.
    poles = st.sampled_from((("no",), ("nc",), ("co",), ("co",), ("no", "nc"), ("co", "co")))
    stateful = draw(st.lists(poles, min_size=size, max_size=size))
    plain = draw(
        st.lists(st.sampled_from(_PLAIN).map(lambda pole: (pole,)), min_size=0, max_size=2)
    )
    items = (*stateful, *plain)
    empty = _Spec(items=items, attachments=(), wires=())
    count = len(_ports(empty))
    index = st.integers(min_value=0, max_value=count - 1)
    attachments = draw(
        st.lists(
            st.tuples(index, st.sampled_from(_RAILS)),
            min_size=2,
            max_size=6,
            unique_by=lambda a: a[0],
        )
    )
    wires = draw(
        st.lists(
            st.tuples(index, index).filter(lambda pair: pair[0] != pair[1]),
            max_size=min(count, 8),
        )
    )
    return _Spec(items=items, attachments=tuple(attachments), wires=tuple(wires))


@settings(max_examples=150, deadline=None, derandomize=True)
@given(_specs())
def test_rail_pairs_equals_the_union_of_the_plain_pairs_over_every_state(spec: _Spec) -> None:
    """Acceptance 3: `rail_pairs` is the brute force over all rest-or-operated assignments."""
    _assert_matches_the_brute_force(spec)


def _assert_matches_the_brute_force(
    spec: _Spec, expected: dict[tuple[int, int], set[tuple[str, str]]] | None = None
) -> None:
    expected = _brute_force(spec) if expected is None else expected
    got = _reads(spec)
    for key in _functions(spec):
        assert got[key] == expected[key], (spec, key)


def test_eight_stateful_items_match_the_brute_force_over_all_256_assignments() -> None:
    """The spec's upper bound end to end: eight items, mixed NO, NC and changeover, two supplies.

    Two chains of contacts feed one load. A changeover common carries both its supplies in the
    every-link model, so the all-links pairing puts one supply across the load; in every real
    state it is one rail, so the brute force does not. Ports: item 0 is 0-2, 1 is 3-4, 2 is 5-6,
    3 is 7-9, 4 is 10-11, 5 is 12-13, 6 is 14-16, 7 is 17-18, the load is 19-20.
    """
    spec = _Spec(
        items=(("co",), ("no",), ("nc",), ("co",), ("no",), ("nc",), ("co",), ("no",), ("load",)),
        attachments=((1, "a1"), (2, "b1"), (8, "a2"), (9, "b2")),
        wires=((0, 15), (14, 3), (4, 5), (6, 19), (6, 17), (18, 20), (7, 12), (13, 10), (11, 20)),
    )
    assert len(_stateful_items(spec)) == 8
    load = (8, 0)
    brute = _brute_force(spec)
    assert brute[load]
    assert brute != _all_closed(spec)
    _assert_matches_the_brute_force(spec, brute)


def _changeover_between_supplies() -> _Spec:
    """A changeover with supply 1 on its break and supply 2 on its make, common on both load ports.

    Ports: 0 com, 1 brk, 2 mk, then the load's 3 and 4.
    """
    return _Spec(
        items=(("co",), ("load",)),
        attachments=((1, "a1"), (2, "b1")),
        wires=((0, 3), (0, 4)),
    )


def test_the_brute_force_finds_no_cross_pair_where_the_all_links_pairing_finds_one() -> None:
    """The oracle tells states apart: a changeover's two supplies never stand on the load at once.

    `port_rails` on the every-link model has the common carry both, so pairing its rails puts
    the two supplies across the load. The brute force does not, and `rail_pairs` agrees with it.
    """
    spec = _changeover_between_supplies()
    load = (1, 0)
    assert _all_closed(spec)[load] == {("a1", "b1")}
    assert _brute_force(spec)[load] == set()
    assert _reads(spec)[load] == frozenset()


def test_a_changeover_pole_itself_keeps_the_open_gap_pair() -> None:
    """Both supplies stand across the pole's own break and make ports in every state."""
    spec = _changeover_between_supplies()
    assert _brute_force(spec)[(0, 0)] == {("a1", "b1")}
    assert _reads(spec)[(0, 0)] == frozenset({("a1", "b1")})


def test_the_union_keeps_a_pair_that_stands_in_one_state_only() -> None:
    """A contact that closes only when operated puts its rail on the load in that state alone."""
    spec = _Spec(
        items=(("no",), ("load",)),
        attachments=((0, "a1"), (3, "a2")),
        wires=((1, 2),),
    )
    load = (1, 0)
    assert _standing(_build(spec, {0: "rest"}), spec)[load] == set()
    assert _standing(_build(spec, {0: "operated"}), spec)[load] == {("a1", "a2")}
    assert _brute_force(spec)[load] == {("a1", "a2")}
    assert _reads(spec)[load] == frozenset({("a1", "a2")})


def test_the_generator_reaches_specs_where_the_states_matter() -> None:
    """Some generated spec has an all-links pair the brute force lacks, and one it agrees on."""
    tuned = settings(max_examples=300, deadline=None, derandomize=True, phases=(Phase.generate,))
    small = _specs().filter(lambda spec: len(_stateful_items(spec)) <= 3)

    def fewer(spec: _Spec) -> bool:
        brute = _brute_force(spec)
        return any(brute[key] != pairs for key, pairs in _all_closed(spec).items())

    def same(spec: _Spec) -> bool:
        brute = _brute_force(spec)
        return any(brute.values()) and brute == _all_closed(spec)

    assert fewer(find(small, fewer, settings=tuned))
    assert same(find(small, same, settings=tuned))
