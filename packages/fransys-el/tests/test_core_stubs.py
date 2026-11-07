"""A lone core marker (a stub) is an off stub whose far end is a conductor's (CORE-TEXTS C).

w07 (a cabinet of lamps on a board's connectors, nested units) is built once for every check. The
lone markers are those of every drawing set's own solve: a set stubs the nets it cuts (R468 U1).
"""
# CONNECTION_NOT_DRAWN 10 per default-salt build set (MATES-DISABLED): mated, harness or board-unit input, refused for 0.22 (R1216).

from dataclasses import replace

import pytest
from conventions_fixtures import house
from fransys_el import build, lay_out_drawn, symbol_kit
from fransys_el.placement_markers import facing_views, stub_fit
from fransys_el.placement_options import options
from fransys_el.placement_sets import bare_pins, cut_lines, drawing_scopes, restrict
from fransys_el.placement_widest import link_fit
from fransys_el.read_markers import drawn_marker
from fransys_el.write_stubs import far_port
from kit_instances import INSTANCES

from electrical_symbols import LIBRARY, MARKER_SLOT
from fransys_layout.core import PinRef, solve
from fransys_model.derive import build_indexes, conductor_ends, port_function
from fransys_model.derive.drawing_text import marker_text
from fransys_model.kernel import ModelError
from fransys_model.layout import LinkMarker, StarKind, layout_of
from fransys_model.vocab.tables import ports

_CORE = ("layout", "core", "link_marker")


def _solved(model, kit, scope, part, chosen):
    """One set's own solve, with the marker boxes `lay_out` fits to its pins (a lead moves them)."""
    pins = [PinRef(s.id, p.id) for s in part.symbols for p in s.pins]
    fit, lines, table = stub_fit(model, kit, (scope.of_unit, LIBRARY), pins)
    turned, above, below = facing_views()
    return solve(
        part,
        replace(
            chosen,
            marker_fit=fit,
            stub_lines=lines,
            stub_table=table,
            link_fit=link_fit(model, kit, LIBRARY, scope.of_unit),
            marker_vertical=turned,
            marker_above=above,
            marker_below=below,
        ),
    )


@pytest.fixture(scope="module")
def built():
    model = INSTANCES["w07"]()
    kit = symbol_kit(model, LIBRARY)
    conventions = house()
    problem, _ = build(model, kit, conventions, LIBRARY)
    bare = bare_pins(model, kit)
    chosen = options(conventions, LIBRARY)
    lines = cut_lines(model, kit)
    parts = [(one, restrict(problem, one, bare, lines)) for one in drawing_scopes(model, kit)]
    core = [_solved(model, kit, one, part, chosen) for one, part in parts]
    written, *_ = lay_out_drawn(model, kit, problem, conventions, LIBRARY)
    stubs = [m for m in layout_of(written, LinkMarker).values() if m.key[:3] == _CORE and m.key[3] == "stub"]
    return model, core, written, stubs


def test_every_lone_core_marker_is_one_off_stub_record(built) -> None:
    _, core, _, stubs = built
    lone = [m for c in core for m in c.annotations.markers if str(m.kind) == "stub"]
    assert len(lone) > 0
    assert len(stubs) == len(lone)
    assert {s.star for s in stubs} == {StarKind.OFF}
    assert all(s.partner == s.id for s in stubs)


def test_a_stub_names_a_conductors_far_end_prints_an_arrow_and_is_drawn_as_a_marker_with_its_text(built) -> None:
    model, _, written, stubs = built
    for stub in stubs:
        at_port = build_indexes(model).conductors_by_port[stub.port]
        assert any(stub.far in conductor_ends(model, c) for c in at_port)
        assert stub.far != stub.port
        text = marker_text(written, stub)
        assert "←" in text or "→" in text
        assert ":" in text
        assert dict(drawn_marker(written, stub, LIBRARY).slots)[MARKER_SLOT] == text


def test_every_listed_pair_of_a_stub_is_a_conductor_at_its_own_port(built) -> None:
    """BUNDLE (R1319): the pairs a stub lists, the first its own, each name a conductor that leaves the pair's port."""
    model, _, _, stubs = built
    assert all(s.pairs[0].port == s.port and s.pairs[0].far == s.far for s in stubs)
    for pair in (p for s in stubs for p in s.pairs):
        assert any(pair.far in conductor_ends(model, c) for c in build_indexes(model).conductors_by_port[pair.port])


def test_a_port_no_conductor_leaves_is_refused_not_guessed() -> None:
    model = INSTANCES["p02"]()
    wired = set(build_indexes(model).conductors_by_port)
    wired_functions = {port_function(model, p) for p in wired}
    free = next(p for p in ports(model) if port_function(model, p) not in wired_functions)
    with pytest.raises(ModelError, match="no conductor leaves its pin"):
        far_port(model, [free])
