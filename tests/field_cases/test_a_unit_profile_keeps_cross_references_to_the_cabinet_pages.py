"""Field case: a unit with interface relays and coils whose contacts stand on other sheets.
The bug: building raised RefError when runs were spliced, as a label named a page of the unit run that the splice drops.
Fixed by model-0192, a cross-reference partner names the page and column of the run that owns its page."""

from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr
from _drawn_pages import drawn_pages

from fransys_model.layout import LinkMarker, Page, layout_of

if TYPE_CHECKING:
    from pathlib import Path

_COUNT = 6


class _Io(NamedTuple):
    strip: Any


def _unit() -> Any:
    @fr.unit("demo-ctl", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
    def unit(u: fr.Design) -> _Io:
        strip = u.terminal_strip("X1", "DEMO-TB-2.5-TWIN", 2 * _COUNT + 8, interface=True)
        contactors = [u.device(f"K{i}", "DEMO-CTR-3P-24") for i in range(_COUNT)]
        relays = [u.device(f"RL{i}", "DEMO-RLY-2CO-24", interface=True) for i in range(_COUNT)]
        for block in range(2):
            with u.function(f"BLK{block}", "Power block"):
                for i, (k, rl) in enumerate(zip(contactors, relays, strict=True)):
                    fuse = u.device(f"F{block}_{i}", "DEMO-FUSE-DC-160")
                    lamp = u.device(f"R{block}_{i}", "DEMO-LAMP-24")
                    u.series(strip[1 + i].inner, fuse.element["1"], wire=("RD", 50))
                    u.series(fuse.element["2"], k.main["1"], wire=("RD", 50))
                    u.series(k.main["2"], lamp["1"], wire=("RD", 50))
                    u.series(lamp["2"], rl.co_1["11"], wire=("RD", 50))
                    u.series(rl.co_1["14"], rl.co_2["21"], wire=("RD", 50))
        with u.function("CTRL", "Control block"):
            for i, (k, rl) in enumerate(zip(contactors, relays, strict=True)):
                u.series(strip[_COUNT + 1 + i].inner, k.coil["A1"], wire=("WH", 0.75))
                u.series(k.coil["A2"], rl.coil["A1"], wire=("WH", 0.75))
                u.series(rl.coil["A2"], strip[2 * _COUNT + 1 + i].inner, wire=("WH", 0.75))
        return _Io(strip)

    return unit


def _build(tmp_path: Path) -> fr.BuildResult:
    d = fr.design("demo_parts")
    d.add(_unit(), "U1")
    (tmp_path / "own.md").write_text("# Control\n", encoding="utf-8")
    cover = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-ctl", cover=tmp_path / "own.md")
    return fr.build(d, cover)


def _assert_every_partner_is_drawn_where_it_names(result: fr.BuildResult) -> None:
    """Each marker's partner stands on a page that exists, drawn, at the marker's own end."""
    model = result.model
    pages = layout_of(model, Page)
    drawn = drawn_pages(model)
    markers = layout_of(model, LinkMarker)
    assert markers
    for marker in markers.values():
        partner = markers[marker.partner]
        assert partner.page in pages
        assert partner.page in drawn


def test_the_unit_cross_references_stay_whole(tmp_path: Path) -> None:
    """A unit with its own page runs keeps every cross-reference partner on a drawn page."""
    result = _build(tmp_path)
    _assert_every_partner_is_drawn_where_it_names(result)
