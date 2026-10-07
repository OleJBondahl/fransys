"""Field case: an interface terminal wired to nothing, with `hide_unused_pins` on.

The engineering shape: a unit hands back two terminals of its interface strip. Only the first
is wired inside the unit; the second is a spare the parent leaves unwired too. The profile hides
unused pins.

The bug: the hide switch dropped the idle terminal's spec while the unit still named it a
boundary function, and `fr.build` raised LayoutError "a unit's boundary names a function that
has no spec" (stages/replicate.py).
The rule (decision layout-0139): `hide_unused_pins` never hides a boundary function. The
findings equal the run without the switch: PORT_UNCONNECTED names the terminal.
"""

from typing import TYPE_CHECKING, NamedTuple

import fransys as fr

from fransys_model.layout import SymbolPlacement, layout_of
from fransys_model.vocab.tables import functions

if TYPE_CHECKING:
    from pathlib import Path


class _Io(NamedTuple):
    used: fr.Terminal
    spare: fr.Terminal


@fr.unit("demo-strip-box", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
def _box(u: fr.Design) -> _Io:
    lamp = u.device("P1", "DEMO-LAMP-24")
    x1 = u.terminal_strip("X1", "DEMO-TB-2.5", interface=True)
    sig = x1.run("SIG", 2)
    u.wire(sig[1], lamp.lamp["1"], wire=("WH", 0.75))
    return _Io(sig[1], sig[2])


def _build(*, hide: bool, tmp_path: Path) -> fr.BuildResult:
    d = fr.design("demo_parts", place="C1")
    cabinet = d.location("C1", "Cabinet")
    d.layout.profile(hide_unused_pins=hide)
    d.add(_box, "U1")
    (tmp_path / "own.md").write_text("# Box\n", encoding="utf-8")
    (tmp_path / "c.md").write_text("# Cabinet\n", encoding="utf-8")
    preset = fr.DocumentPreset.CABINET_SCHEMATIC
    own = fr.document(preset, "demo-strip-box", cover=tmp_path / "own.md")
    return fr.build(d, own, fr.document(preset, cabinet, cover=tmp_path / "c.md"))


def _findings(result: fr.BuildResult) -> list[tuple[str, str]]:
    return sorted((f.code, str(f.subjects)) for f in result.findings)


def _drawn(result: fr.BuildResult) -> list[tuple]:
    """The key of every function the layout draws, with its count."""
    model = result.model
    return sorted(
        functions(model)[p.function].key for p in layout_of(model, SymbolPlacement).values()
    )


def test_an_idle_boundary_terminal_builds_and_keeps_its_findings(tmp_path: Path) -> None:
    """No exception with the switch on; findings and drawn functions equal the run with it off."""
    for sub in "ab":
        (tmp_path / sub).mkdir()
    plain = _build(hide=False, tmp_path=tmp_path / "a")
    hidden = _build(hide=True, tmp_path=tmp_path / "b")
    assert _findings(hidden) == _findings(plain)
    assert _drawn(hidden) == _drawn(plain)
    assert any(f.code == "PORT_UNCONNECTED" for f in hidden.findings)
