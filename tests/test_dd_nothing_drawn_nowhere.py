"""Rule 7 (layout-0080): nothing is drawn nowhere in silence, `check_nowhere` under the exemptions.

A nested unit's boundary pin may draw nothing in a set (rules 5 and 6); the guard is the net
under that: a net whose members all draw nothing, in every set, is `CONNECTION_NOT_DRAWN`.
Built through the `fransys` facade from `examples/demo-parts`, the nested-unit wire of
`test_dd_boundary_draw` (unit `p`, nested unit `ua` with boundary connector `f`, item `h` in `p`,
wire `f.1` to `h.1`) is drawn in `p`'s set: no error. The layout of that build with the routes
and markers of the net removed is what the guard must find, once, naming the two ports.
"""

import dataclasses
import importlib.util
from pathlib import Path

from fransys_layout.engines.schematic import engine, run_stages
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.lint import check_nowhere
from fransys_layout.lint.codes import CONNECTION_NOT_DRAWN
from fransys_model.kernel import Finding, Severity


def _load(name: str):
    """A sibling root test module, loaded by path (root tests are not a package)."""
    spec = importlib.util.spec_from_file_location(name[:-3], Path(__file__).with_name(name))
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_DRAW = _load("test_dd_boundary_draw.py")


def test_a_nested_units_wire_is_drawn_and_the_guard_is_silent() -> None:
    """The healthy build: no ERROR, and `check_nowhere` finds nothing in its layout.

    # UNDO: none of its own: the healthy-path twin of the can-fail test below, which fails when
    #   the guard is silenced (this one fails only if a healthy build's net stops being drawn)
    """
    result = _DRAW._build_nested_wire()
    assert not [f for f in result.findings if f.severity is Severity.ERROR]
    inputs = read_inputs(result.model)
    layout, drawn, _findings = run_stages(result.model, inputs)
    assert check_nowhere(layout, inputs.connections, inputs.net_groups, drawn) == ()


def test_the_engine_reports_what_the_guard_finds(monkeypatch) -> None:
    """The wiring: a build's findings hold what `check_nowhere` returns for the run's layout.

    The guard is replaced in the engine by one that finds a sentinel net, so the assert holds
    only if `_lint_findings` calls it and passes its result on (the `fr.write` refusal on ERROR
    follows from that severity).

    # UNDO: engines/schematic/engine.py, delete the `check_nowhere` call in `_lint_findings`
    """
    marker = Finding(
        code=CONNECTION_NOT_DRAWN, severity=Severity.ERROR, subjects=(), message="sentinel"
    )
    monkeypatch.setattr(engine, "check_nowhere", lambda *_args, **_kwargs: (marker,))
    result = _DRAW._build_nested_wire()
    assert marker in result.findings


def test_a_stubbed_conductor_is_drawn_by_its_stubs_and_nowhere_without_them() -> None:
    """A top-level unit's boundary pin wired to a top-level item at the same location ends in
    stubs (rule 7 names "stub" as a cover). The guard over the stubbed conductor finds nothing
    in the healthy layout, and once, naming the two ports, in the layout with its markers gone.

    # UNDO: lint/members.py, `check_nowhere` ignores `layout.markers` (the first assert fails)
    """
    model = _DRAW._build_top_level_units(second_unit=False, same=True).model
    ends = {_DRAW._pin_one(model, "f"), _DRAW._pin_one(model, "h")}
    inputs = read_inputs(model)
    layout, drawn, _findings = run_stages(model, inputs)
    stubbed = (*inputs.connections, *inputs.crossing)
    assert check_nowhere(layout, stubbed, inputs.net_groups, drawn) == ()
    bare = dataclasses.replace(layout, markers=())
    (found,) = check_nowhere(bare, stubbed, inputs.net_groups, drawn)
    assert found.code == CONNECTION_NOT_DRAWN
    assert found.subjects == tuple(sorted(ends))


def test_the_engine_hands_the_guard_the_stubbed_conductors(monkeypatch) -> None:
    """`_lint_findings` gives `check_nowhere` the conductors that end in stubs too: the one of
    the same build as above reaches it, ends `f.1` and `h.1`.

    # UNDO: engines/schematic/engine.py, `_lint_findings` passes `connections` alone to
    #   `check_nowhere` (the crossing conductors are not in it)
    """
    given = []
    real = engine.check_nowhere

    def spy(layout, connections, *rest):
        given.append(connections)
        return real(layout, connections, *rest)

    monkeypatch.setattr(engine, "check_nowhere", spy)
    result = _DRAW._build_top_level_units(second_unit=False, same=True)
    ends = {_DRAW._pin_one(result.model, "f"), _DRAW._pin_one(result.model, "h")}
    (seen,) = given
    assert any({c.a.port, c.b.port} == ends for c in seen)


def test_the_same_layout_without_the_nets_routes_and_markers_is_drawn_nowhere() -> None:
    """The can-fail: strip every route end and marker on `f.1` and `h.1`; the guard fires once.

    # UNDO: lint/members.py, `check_nowhere` returns nothing, or ignores the markers or routes
    """
    model = _DRAW._build_nested_wire().model
    ends = {_DRAW._pin_one(model, "f"), _DRAW._pin_one(model, "h")}
    inputs = read_inputs(model)
    layout, drawn, _findings = run_stages(model, inputs)
    assert any(r.a in ends or r.b in ends for r in layout.routes) or any(
        m.port in ends for m in layout.markers
    ), "the healthy layout draws the net somewhere"
    bare = dataclasses.replace(
        layout,
        routes=tuple(r for r in layout.routes if not {r.a, r.b} & ends),
        markers=tuple(m for m in layout.markers if m.port not in ends),
    )
    (found,) = check_nowhere(bare, inputs.connections, inputs.net_groups, drawn)
    assert found.code == CONNECTION_NOT_DRAWN
    assert found.severity is Severity.ERROR
    assert found.subjects == tuple(sorted(ends))
