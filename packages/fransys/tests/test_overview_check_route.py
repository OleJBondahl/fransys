"""`check` runs the overview engine and `write` gates on it (OVERVIEW O25, acceptance A9).

`build` never runs it, so a build with no document lays nothing out. A planted ERROR from the
overview call stops every write, whole-system or one unit's, before any file is written.
"""

import fransys as fr
import fransys_author
import pytest
from demo_designs import cabinet_design
from fransys import BuildErrors, pipeline

from fransys_model.kernel import Finding, Severity
from fransys_model.vocab import units

_PLANTED = "DIAGRAM_BOX_OVERLAP"


def _plant_error(monkeypatch):
    """Make the overview call report one ERROR for any model."""
    error = Finding(code=_PLANTED, severity=Severity.ERROR, subjects=(), message="planted")
    monkeypatch.setattr(pipeline, "_overview", lambda model: (model, (error,)))


def _unit_draft(parts):
    """One unit with a relay and a field strip, two wires, no document."""
    design = fransys_author.Design(parts)
    scope = design.scope("unit").unit("unit", revision=1, interface="1")
    scope.revision(1, date="2026-09-26", text="First issue", created="XX")
    cab = scope.location("CAB", "Cabinet")
    supply = scope.group("SUP", "Supply")
    strip = scope.strip("X01", at=cab)
    relay = scope.item("DEMO-CO-4P-24", tag="K1", at=cab, group=supply)
    wire = scope.wiring(colour="BK", gauge="1.5")
    for pole in (3, 4):
        terminal = strip.terminal("DEMO-TB-2.5", f"RUN{pole}", group=supply)
        wire(terminal.inner, relay.fn(f"co_{pole}")[f"{pole}4"])
    return design.draft()


def _built():
    parts = fr.parts("demo_parts")
    return fr.build(parts, cabinet_design(parts).draft())


def test_build_runs_no_overview_engine_but_check_and_write_do(tmp_path):
    """Fails if `build` calls the overview engine (A9) or if `check`/`write` stop calling it."""
    pipeline._overview.cache_clear()
    result = _built()
    assert pipeline._overview.builds == 0
    fr.check(result)
    assert pipeline._overview.builds == 1
    written = fr.write(result, tmp_path / "out")
    assert pipeline._overview.builds == 1, "write reuses check's one pure call"
    assert any(path.suffix == ".html" for path in written), [p.name for p in written]


def test_check_returns_the_overview_findings(monkeypatch):
    """Fails if `check` stops adding the overview engine's findings."""
    result = _built()
    assert _PLANTED not in {f.code for f in fr.check(result)}
    _plant_error(monkeypatch)
    assert _PLANTED in {f.code for f in fr.check(result)}


def test_write_gates_on_an_overview_error_and_writes_nothing(tmp_path, monkeypatch):
    """Fails if a system write goes ahead past an overview ERROR."""
    result = _built()
    _plant_error(monkeypatch)
    with pytest.raises(BuildErrors):
        fr.write(result, tmp_path / "out")
    out = tmp_path / "out"
    assert not out.exists() or not any(out.iterdir())


def test_a_unit_write_gates_on_an_overview_error_too(tmp_path, monkeypatch):
    """Fails if a unit write skips the overview findings."""
    parts = fr.parts("demo_parts")
    result = fr.build(parts, _unit_draft(parts))
    unit = next(iter(units(result.model)))
    _plant_error(monkeypatch)
    with pytest.raises(BuildErrors):
        fr.write(result, tmp_path / "out", unit=unit)
