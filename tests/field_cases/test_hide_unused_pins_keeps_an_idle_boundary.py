"""Field case: a unit hands back two interface terminals, only one wired inside, with hide_unused_pins on.
The bug: the hide switch dropped the idle terminal's spec while the unit still named it a boundary function, so fr.build raised LayoutError.
Fixed by layout-0139, hide_unused_pins never hides a boundary function, and the findings equal the run without the switch."""

from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr
from _drawn_pages import drawn_pages

if TYPE_CHECKING:
    from pathlib import Path


class _Io(NamedTuple):
    used: fr.Terminal
    spare: fr.Terminal


def _box(*, hide: bool) -> Any:
    """The unit; with `hide` it sets the profile in its own body (the unit's, model-0192)."""

    @fr.unit("demo-strip-box", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
    def box(u: fr.Design) -> _Io:
        if hide:
            u.layout.profile(hide_unused_pins=True)
        lamp = u.device("P1", "DEMO-LAMP-24")
        x1 = u.terminal_strip("X1", "DEMO-TB-2.5", interface=True)
        sig = x1.run("SIG", 2)
        u.series(sig[1].inner, lamp.lamp["1"], wire=("WH", 0.75))
        u.series(lamp.lamp["2"], u.device("G1", None, external=True, pins=("P",)).P, wire=("WH", 0.75))
        return _Io(sig[1], sig[2])

    return box


def _build(*, hide: bool, tmp_path: Path) -> fr.BuildResult:
    d = fr.design("demo_parts", place="C1")
    cabinet = d.location("C1", "Cabinet")
    d.add(_box(hide=hide), "U1")
    (tmp_path / "own.md").write_text("# Box\n", encoding="utf-8")
    (tmp_path / "c.md").write_text("# Cabinet\n", encoding="utf-8")
    preset = fr.DocumentPreset.CABINET_SCHEMATIC
    own = fr.document(preset, "demo-strip-box", cover=tmp_path / "own.md")
    return fr.build(d, own, fr.document(preset, cabinet, cover=tmp_path / "c.md"))


def _findings(result: fr.BuildResult) -> list[tuple[str, str]]:
    return sorted((f.code, str(f.subjects)) for f in result.findings)


def _drawn(result: fr.BuildResult) -> list[tuple[Any, ...]]:
    """The key and markings of every symbol the layout draws, with its count."""
    return sorted((symbol.key, symbol.slots) for drawing in drawn_pages(result.model).values() for symbol in drawing.symbols)


def test_an_idle_boundary_terminal_builds_and_keeps_its_findings(tmp_path: Path) -> None:
    """No exception with the switch on; findings and drawn functions equal the run with it off."""
    for sub in "ab":
        (tmp_path / sub).mkdir()
    plain = _build(hide=False, tmp_path=tmp_path / "a")
    hidden = _build(hide=True, tmp_path=tmp_path / "b")
    assert _findings(hidden) == _findings(plain)
    assert _drawn(hidden) == _drawn(plain)
