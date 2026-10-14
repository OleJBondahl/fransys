"""Field case: an unwired interface redundancy device, with `hide_unused_pins` on.

The engineering shape: a unit hands back a redundancy module of its interface that nothing is
wired to, next to a lamp that nothing is wired to, and sets `hide_unused_pins` on its own profile.

The bug: building raised RefError "the id names no record" when the layout runs were spliced
(splice.py `spliced`). A page id follows its first drawn group. The unit hides its spare lamp, so
its own run named its page differently, and the cabinet's cross-reference kept the top run's id.
The rule: a spliced cross-reference names the page and the column the unit's own run draws.
Hiding the lamps shifts the interface port's column, so the base run's x would print a stale cell.
"""

from dataclasses import replace
from typing import TYPE_CHECKING, NamedTuple

import fransys as fr

from fransys_model.derive.drawing_text import cross_reference_text
from fransys_model.layout import Label, layout_of

if TYPE_CHECKING:
    from pathlib import Path


class _Io(NamedTuple):
    lamp: fr.Device


@fr.unit("demo-idle-red", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
def _box(u: fr.Design) -> _Io:
    u.layout.profile(hide_unused_pins=True)
    for tag in ("P1", "P2", "P3"):
        u.device(tag, "DEMO-LAMP-24")
    return _Io(u.device("X1", "DEMO-RED-2IN", interface=True))


def test_an_unwired_redundancy_interface_builds(tmp_path: Path) -> None:
    """The unit's own page and the cabinet page place."""
    d = fr.design("demo_parts", place="C1")
    cabinet = d.location("C1", "Cabinet")
    d.add(_box, "U1")
    (tmp_path / "own.md").write_text("# Box\n", encoding="utf-8")
    (tmp_path / "c.md").write_text("# Cabinet\n", encoding="utf-8")
    preset = fr.DocumentPreset.CABINET_SCHEMATIC
    own = fr.document(preset, "demo-idle-red", cover=tmp_path / "own.md")
    result = fr.build(d, own, fr.document(preset, cabinet, cover=tmp_path / "c.md"))
    labels = [one for one in layout_of(result.model, Label).values() if one.partners]
    own_x = {e.port: e.x for one in labels for e in one.partners if e.page == one.page}
    spliced = [
        one for one in labels if one.partners[0].port in own_x and one.partners[0].page != one.page
    ]
    assert spliced
    for one in spliced:
        end = one.partners[0]
        unit_end = replace(end, x=own_x[end.port])
        assert end.x != 0
        assert cross_reference_text(result.model, one) == cross_reference_text(
            result.model, replace(one, partners=(unit_end,))
        )
