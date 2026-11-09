"""Field case: with `[export] hide_pe` a PE strip terminal joined by d.earth raised CONNECTION_NOT_DRAWN.
The bug: the sheets leave the PE conductors out, yet the drawn netlist still counted the earth-joined PE net as required.
Fixed by HIDE-PE-EARTH, every PE conductor the sheets leave out is exempt however the net is joined."""

lazy from pathlib import Path

import fransys as fr
from _model_build_cover import unit_document
from fransys.colours import BK, GNYE


def _build(tmp_path: Path, *, hide: bool, runs: bool = False) -> fr.BuildResult:
    toml = tmp_path / "fransys.toml"
    toml.write_text(f"[export]\nhide_pe = {str(hide).lower()}\n")
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    x0 = d.terminal_strip("X0", "DEMO-TB-2.5-TWIN")
    ac = d.ac_supply("400V", "230", x0[1], x0[2], x0[3], n=x0[4])
    pe = d.terminal_strip("PE", "DEMO-TB-PE-2.5", 2, bridged=True)
    with d.function("FAN", "Fan"):
        q1 = d.device("Q1", "DEMO-CTR-3P-24")
        f1 = d.device("F1", "DEMO-OVERLOAD-3P")
        m1 = d.device("M1", "DEMO-MOTOR-4KW")
        w1 = d.cable("W1", "DEMO-CBL-4G1.5")
        d.series(ac, q1.main, f1.main, wire=(BK, 2.5))
        w1.core(GNYE, pe[1].outer, m1.motor.PE)
        d.series(f1.main, w1, m1.motor)
        d.earth(pe[2].outer)
        if runs:
            ends = [d.terminal_strip(f"PE{k}", "DEMO-TB-PE-2.5", 1, interface=False) for k in (3, 4, 5)]
            d.earth(*(e[1].outer for e in ends))
    return fr.build(d, unit_document(cab), settings=fr.settings(toml))


def _cnd(result: fr.BuildResult) -> list[fr.Finding]:
    return [f for f in result.findings if f.code == "CONNECTION_NOT_DRAWN"]


def test_a_hidden_pe_terminal_joined_by_earth_is_not_a_missing_connection(tmp_path: Path) -> None:
    """The guide: a PE conductor the sheets leave out is not required, not carried and not missing."""
    result = _build(tmp_path, hide=True)
    assert not _cnd(result)
    fr.write(result, tmp_path / "out")


def test_three_earth_joined_pe_strips_are_exempt_too(tmp_path: Path) -> None:
    """The legacy shape: several PE strips joined by one d.earth."""
    result = _build(tmp_path, hide=True, runs=True)
    assert not _cnd(result)
    fr.write(result, tmp_path / "out")


def test_with_hide_pe_off_the_same_build_reports_what_it_did(tmp_path: Path) -> None:
    """hide_pe = false stays as before: no error, and the earth-joined PE net is drawn."""
    result = _build(tmp_path, hide=False)
    assert not [f for f in _cnd(result) if f.severity == fr.Severity.ERROR]
