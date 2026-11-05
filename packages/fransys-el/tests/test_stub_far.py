"""The far end and cable a stub names are `derive.stub_far`'s (CORE-TEXTS FIX3, parts 1 and 2).

p02 holds pins no conductor leaves (a terminal's unwired side); w07 holds pins that reach several
conductors and conductors carried by a cable.
"""
# CONNECTION_NOT_DRAWN 10 per default-salt build set (MATES-DISABLED): mated, harness or board-unit input, refused for 0.22 (R1216).

from dataclasses import replace

import pytest
from conventions_fixtures import house
from fransys_el import build, lay_out_drawn, symbol_kit
from fransys_el.placement_sets import drawing_scopes
from fransys_el.write_stubs import stub_ends
from kit_instances import INSTANCES

from electrical_symbols import LIBRARY
from fransys_layout.core import PinRef
from fransys_model.derive import build_indexes, conductor_ends, far_pins, stub_far
from fransys_model.derive.drawing_text import marker_text
from fransys_model.kernel import Origin, evolve
from fransys_model.layout import LinkMarker, StarKind, layout_of
from fransys_model.vocab.tables import ports


def _far(model, port, conductor):
    a, b = conductor_ends(model, conductor)
    return b if a == port else a


def _reach(model, near):
    by_port = build_indexes(model).conductors_by_port
    return [(p, _far(model, p, c)) for p in near for c in by_port.get(p, ())]


@pytest.fixture(scope="module")
def p02():
    return INSTANCES["p02"]()


@pytest.fixture(scope="module")
def w07():
    return INSTANCES["w07"]()


def test_a_pin_none_wires_takes_a_conductor_of_its_function(p02) -> None:
    ix = build_indexes(p02)
    unwired = [p for p in ports(p02) if p not in ix.conductors_by_port]
    checked = 0
    for port in unwired:
        siblings = ix.ports_by_function[ports(p02)[port].function]
        expected = _reach(p02, siblings)
        found = stub_far(p02, [port])
        if not expected:
            assert found == ()
            continue
        assert found
        assert (found[0][0], found[0][1]) == min(expected, key=lambda pair: (pair[1], pair[0]))
        checked += 1
    assert checked > 0


def test_a_wired_pin_names_its_own_conductor_and_not_its_functions(w07) -> None:
    ix = build_indexes(w07)
    for port in ix.conductors_by_port:
        found = stub_far(w07, [port])
        assert found
        assert all(end[0] == port and end[:2] in _reach(w07, [port]) for end in found)


def test_several_reaches_tie_on_the_first_far_end_by_designation(w07) -> None:
    ix = build_indexes(w07)
    many = [p for p, cs in ix.conductors_by_port.items() if len(cs) > 1]
    assert many
    for port in many:
        found = stub_far(w07, [port])
        assert found
        assert found[0][1] == far_pins(w07, [port])[0][1]


def test_a_stub_names_the_far_end_it_is_given(w07) -> None:
    """R1581: a stub end names its conductor: the far end given, whichever the first by designation is."""
    ix = build_indexes(w07)
    many = [p for p in ix.conductors_by_port if len({f for _, f in _reach(w07, [p])}) > 1]
    assert many
    for port in many:
        (_, first), *_, (_, last) = far_pins(w07, [port])
        assert (stub_ends(w07, [port]) or ((None, None),))[0][1] == first
        assert (stub_ends(w07, [port], [last]) or ((None, None),))[0][1] == last


def test_a_pin_no_conductor_reaches_has_no_far_end(p02) -> None:
    ix = build_indexes(p02)
    wired_functions = {ports(p02)[p].function for p in ix.conductors_by_port}
    free = [p for p in ports(p02) if ports(p02)[p].function not in wired_functions]
    for port in free:
        assert stub_far(p02, [port]) == ()


def _unwired(problem, scopes):
    """`problem` with each pin of a symbol in one set given one conductor to a pin outside: no wire is drawn, so the cut stubs it (R407)."""
    held = [s for scope in scopes for s in scope.symbols]
    near = dict.fromkeys(a for a, _ in problem.facts.far_ends if held.count(a.sym) == 1)
    out = tuple((n, PinRef("out", f"{n.sym}.{n.pin}")) for n in near)
    return replace(problem, facts=replace(problem.facts, far_ends=out, groups=out))


@pytest.fixture(scope="module")
def w07_stubs(w07):
    kit = symbol_kit(w07, LIBRARY)
    conventions = house()
    problem, _ = build(w07, kit, conventions, LIBRARY)
    # no far end: every crossing end stubs, as R407 has it where no wire is drawn
    problem = _unwired(problem, drawing_scopes(w07, kit))
    # the built layout's markers go, so the new ones collide with none of their ids
    bare = evolve(w07, remove=tuple(layout_of(w07, LinkMarker)), origin=Origin(file=__file__, line=0, note="w07 without its markers"))
    written, *_ = lay_out_drawn(bare, kit, problem, conventions, LIBRARY)
    stubs = [m for m in layout_of(written, LinkMarker).values() if m.star is StarKind.OFF]
    return written, stubs


def test_a_stub_on_a_cable_carries_it_and_prints_its_designation(w07_stubs) -> None:
    written, stubs = w07_stubs
    carried = [s for s in stubs if s.pairs[0].carrier is not None]
    assert carried
    for stub in carried:
        assert marker_text(written, stub).split(" ")[0] not in "←→"
        assert "-W" in marker_text(written, stub).split(" ")[0]


def test_a_stub_on_a_wire_has_no_cable_part(w07_stubs) -> None:
    written, stubs = w07_stubs
    bare = [s for s in stubs if s.pairs[0].carrier is None]
    assert bare
    assert all(marker_text(written, s)[0] in "←→" for s in bare)
