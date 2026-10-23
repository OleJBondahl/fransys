"""A lone core marker (a stub) is an off stub whose far end is a conductor's (CORE-TEXTS C).

p02 (a unit strip wired to a module and on to a field strip) is built once for every check. The
lone markers are those of every drawing set's own solve: a set stubs the nets it cuts (R468 U1).
"""

from dataclasses import replace

import pytest
from conventions_fixtures import house
from fransys_el import ProblemError, build, lay_out, options, symbol_kit
from fransys_el.placement_markers import facing_views, marker_fit
from fransys_el.placement_sets import bare_pins, cut_lines, drawing_scopes, restrict
from fransys_el.placement_widest import link_fit
from fransys_el.read_markers import drawn_marker
from fransys_el.write_stubs import far_port
from kit_instances import INSTANCES

from electrical_symbols import LIBRARY, MARKER_SLOT
from fransys_layout.core import PinRef, solve
from fransys_model.derive import build_indexes, conductor_ends
from fransys_model.derive.drawing_text import marker_text
from fransys_model.layout import LinkMarker, StarKind, layout_of
from fransys_model.vocab.tables import ports

_CORE = ("layout", "core", "link_marker")


def _solved(model, kit, scope, part, chosen):
    """One set's own solve, with the marker boxes `lay_out` fits to its pins (a lead moves them)."""
    pins = [PinRef(s.id, p.id) for s in part.symbols for p in s.pins]
    fit = marker_fit(model, kit, scope.of_unit, LIBRARY, pins)
    turned, above, below = facing_views()
    return solve(
        part,
        replace(
            chosen,
            marker_fit=fit,
            link_fit=link_fit(model, kit, LIBRARY, scope.of_unit),
            marker_vertical=turned,
            marker_above=above,
            marker_below=below,
        ),
    )


@pytest.fixture(scope="module")
def built():
    model = INSTANCES["p02"]()
    kit = symbol_kit(model, LIBRARY)
    conventions = house()
    problem, _ = build(model, kit, conventions, LIBRARY)
    bare = bare_pins(model, kit)
    chosen = options(conventions, LIBRARY)
    lines = cut_lines(model, kit)
    parts = [(one, restrict(problem, one, bare, lines)) for one in drawing_scopes(model, kit)]
    core = [_solved(model, kit, one, part, chosen) for one, part in parts]
    written, _ = lay_out(model, kit, problem, conventions, LIBRARY)
    stubs = [
        m
        for m in layout_of(written, LinkMarker).values()
        if m.key[:3] == _CORE and m.key[3] == "stub"
    ]
    return model, core, written, stubs


def test_every_lone_core_marker_is_one_off_stub_record(built) -> None:
    _, core, _, stubs = built
    lone = [m for c in core for m in c.annotations.markers if str(m.kind) == "stub"]
    assert len(lone) > 0
    assert len(stubs) == len(lone)
    assert {s.star for s in stubs} == {StarKind.OFF}
    assert all(s.partner == s.id for s in stubs)


def test_a_stubs_far_end_is_the_other_end_of_a_conductor_at_its_port(built) -> None:
    model, _, _, stubs = built
    for stub in stubs:
        at_port = build_indexes(model).conductors_by_port[stub.port]
        assert any(stub.far in conductor_ends(model, c) for c in at_port)
        assert stub.far != stub.port


def test_a_stub_prints_an_arrow_and_its_far_device(built) -> None:
    _, _, written, stubs = built
    for stub in stubs:
        text = marker_text(written, stub)
        assert "←" in text or "→" in text
        assert ":" in text


def test_a_port_no_conductor_leaves_is_refused_not_guessed(built) -> None:
    model, _, _, _ = built
    wired = set(build_indexes(model).conductors_by_port)
    free = next(p for p in ports(model) if p not in wired)
    with pytest.raises(ProblemError, match="no conductor leaves its pin"):
        far_port(model, [free])


def test_a_stub_is_drawn_as_a_marker_symbol_with_its_text(built) -> None:
    _, _, written, stubs = built
    for stub in stubs:
        drawn = drawn_marker(written, stub, LIBRARY)
        assert dict(drawn.slots)[MARKER_SLOT] == marker_text(written, stub)
