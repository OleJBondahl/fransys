"""The member check (layout-0071) is wired into the engine, and reads the net before its stars.

The PE net of `test_dd_star_per_set` is three terminals: the hub `-X1:1` wired to `-X3:1` and
`-X3:2`. In the unit's own set, on a page of its own (`fill` 3), `-X3:1` stands apart from the
hub and is covered by a branch marker, which the star pass makes; on the hub's page (`fill` 1)
M12 joins the three by wires, so routes cover them. `check_members` is handed the connections
and net groups from before the star nets are taken out, and the full layout with the star
markers. Built through the
`fransys` facade from `examples/demo-parts`: the build reports no `CONNECTION_NOT_DRAWN`, and
the same build with the star pass making no branch (`stages.references.nets.branch_pages`, as
`references.markers` calls it, returns nothing)
reports it for the branch-less ports, so the negative is proved by the positive twin.
"""

import importlib.util
from pathlib import Path

import fransys as fr
import pytest

import fransys_layout.stages.references.markers as star
from fransys_layout.lint.codes import CONNECTION_NOT_DRAWN
from fransys_model.derive.designation import port_designation
from fransys_model.layout import Route, layout_of


def _load(name: str):
    """A sibling root test module, loaded by path (root tests are not a package)."""
    spec = importlib.util.spec_from_file_location(name[:-3], Path(__file__).with_name(name))
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_STAR = _load("test_dd_star_per_set.py")


def _recorded_build(monkeypatch: pytest.MonkeyPatch, fill: int) -> list:
    """Run the star fixture's build, and return every `fr.build` result it made.

    The fixture's own no-ERROR assert may fail; the result is recorded before that.
    """
    built: list = []
    real = fr.build

    def recording(*args, **kwargs):
        built.append(real(*args, **kwargs))
        return built[-1]

    monkeypatch.setattr(fr, "build", recording)
    try:
        _STAR._build(_STAR._APART, fill=fill)
    except AssertionError:
        assert built, "the build itself failed"
    return built


@pytest.mark.parametrize("fill", [1, 3], ids=["same-page", "other-page"])
def test_a_star_net_with_branch_markers_reports_no_member_not_drawn(
    fill: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every placed member of the PE net has a route or a marker in its set: no finding.

    # UNDO: lint/members.py, `check_members` returns `CONNECTION_NOT_DRAWN` for every member
    """
    (result,) = _recorded_build(monkeypatch, fill)
    assert [f for f in result.findings if f.code == CONNECTION_NOT_DRAWN] == []


@pytest.mark.parametrize("fill", [1, 3], ids=["same-page", "other-page"])
def test_a_star_net_without_its_branches_reports_the_branch_less_ports(
    fill: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With the star pass making no branch, the build reports the ports that lose theirs.

    The positive twin of the test above: it proves the engine calls `check_members` and that the
    finding reaches `fr.build`'s findings, an ERROR, as `fr.write` refuses on it. On one page
    (`fill` 1) M12 joins the PE terminals by wires, so they lose no branch: the ports named are
    the relays' of the fixture's other nets, which are still stars, and the routes stand for
    the terminals.

    # UNDO: engines/schematic/engine.py, delete the `check_members` call in `_lint_findings`
    """
    monkeypatch.setattr(star, "branch_pages", lambda *_args, **_kwargs: [])
    (result,) = _recorded_build(monkeypatch, fill)
    model = result.model
    hits = [f for f in result.findings if f.code == CONNECTION_NOT_DRAWN]
    assert hits
    assert {f.severity.name for f in hits} == {"ERROR"}
    # a finding's subjects are the port and the conductors that end at it (layout-0077), in Id order
    named = {
        port_designation(model, subject)
        for f in hits
        for subject in f.subjects
        if subject.kind == "port"
    }
    if fill == 1:
        ends = {
            port_designation(model, end)
            for route in layout_of(model, Route).values()
            for end in (route.a, route.b)
        }
        assert all(any(name.endswith(f"-X3:{n}") for name in ends) for n in (1, 2))
        assert not [name for name in named if name.startswith("-X3:")], named
        assert any(name.startswith("-K") for name in named), named
    else:
        assert any(name.startswith("-X3:") for name in named), named
