"""Field case: a unit with its own layout profile, interface relays and cross-page coils.

The engineering shape: one unit added alone holds six contactors and six relays, the relays
handed back as interface devices. Each contactor's coil is wired in a control block and its main
contacts in two power blocks, so coil and contact stand on separate sheets. A relay's contacts
stand on the unit's sheets and again on the parent's sheets, which cross-refer to each other.
The unit's profile and the design's differ in `column_gap`, so the two layout runs page the
parent's sheets differently.

The bug: building raised RefError "the id names no record" (profile on the design or in the
unit body) when the runs were spliced (splice.py `spliced`). A unit's label names its partner on
a parent sheet by the unit run's own page id and column. The splice took the home of such a
partner from the unit run too, a sheet the splice drops, so the label named a page that no longer
exists. Where the sheet id differs between the runs this is a RefError; where it is equal the
column was the unit run's, not the parent's.
The rule (model-0192): a cross-reference partner names the page and
column of the run that owns its page, the unit's run for the unit's sheets, the base run for the
rest.

Each test builds once: the two profiles place differently, so they share nothing to reuse.
"""

from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr
from _drawn_pages import drawn_pages

from fransys_model.layout import LinkMarker, Page, layout_of

if TYPE_CHECKING:
    from pathlib import Path

_UNIT_GAP = 64
_DESIGN_GAP = 8
_COUNT = 6


class _Io(NamedTuple):
    strip: Any


def _unit(gap: int | None) -> Any:
    @fr.unit("demo-ctl", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
    def unit(u: fr.Design) -> _Io:
        if gap is not None:
            u.layout.profile(column_gap=gap)
        strip = u.terminal_strip("X1", "DEMO-TB-2.5", 2 * _COUNT + 8, interface=True)
        contactors = [u.device(f"K{i}", "DEMO-CTR-3P-24") for i in range(_COUNT)]
        relays = [u.device(f"RL{i}", "DEMO-RLY-2CO-24", interface=True) for i in range(_COUNT)]
        for block in range(2):
            with u.function(f"BLK{block}", "Power block"):
                for i, (k, rl) in enumerate(zip(contactors, relays, strict=True)):
                    fuse = u.device(f"F{block}_{i}", "DEMO-FUSE-DC-160")
                    lamp = u.device(f"R{block}_{i}", "DEMO-LAMP-24")
                    u.detail.wire(strip[1 + i], fuse.element["1"], wire=("RD", 50))
                    u.detail.wire(fuse.element["2"], k.main["1"], wire=("RD", 50))
                    u.detail.wire(k.main["2"], lamp["1"], wire=("RD", 50))
                    u.detail.wire(lamp["2"], rl.co_1["11"], wire=("RD", 50))
                    u.detail.wire(rl.co_1["14"], rl.co_2["21"], wire=("RD", 50))
        with u.function("CTRL", "Control block"):
            for i, (k, rl) in enumerate(zip(contactors, relays, strict=True)):
                u.detail.wire(strip[_COUNT + 1 + i], k.coil["A1"], wire=("WH", 0.75))
                u.detail.wire(k.coil["A2"], rl.coil["A1"], wire=("WH", 0.75))
        return _Io(strip)

    return unit


def _build(tmp_path: Path, *, design: int | None, in_body: int | None) -> fr.BuildResult:
    d = fr.design("demo_parts")
    if design is not None:
        d.layout.profile(column_gap=design)
    d.add(_unit(in_body), "U1")
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


def test_the_design_profile_leaves_the_unit_cross_references_whole(tmp_path: Path) -> None:
    """The design narrows the gap; the unit draws with the house gap."""
    result = _build(tmp_path, design=_DESIGN_GAP, in_body=None)
    _assert_every_partner_is_drawn_where_it_names(result)


def test_the_unit_body_profile_leaves_the_unit_cross_references_whole(tmp_path: Path) -> None:
    """The unit widens the gap in its body; the design has no profile."""
    result = _build(tmp_path, design=None, in_body=_UNIT_GAP)
    _assert_every_partner_is_drawn_where_it_names(result)
