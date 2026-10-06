"""layout-0117: a row of pins whose power symbol reaches into the box it faces moves, whole.

The shape (the pump station's): a DO module's box above a 2-pin plug's pin row (contact-male
R0, ports facing N), the mated board's pins below it as face cells (R180). Plug pin 2 sits on
the 0 V rail, so its ground stands on the pin and points up into the box. At `row_gap=32` the
one-grid lead reaches the box; at 64 it clears. The rule's absence is `clear_symbols` patched
to a no-op and the same model laid out again.
"""

from decimal import Decimal
from typing import TYPE_CHECKING, Any

import fransys as fr
import pytest
from fransys.colours import BU

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.geometry import Box, Orientation, symbol_geometry, translate
from fransys_layout.stages import stack_room
from fransys_layout.stages.lookups import placed_keepout
from fransys_layout.stages.texts.power_lead import POWER_SYMBOL_UNPLACED
from fransys_model.layout import PowerSymbol, layout_of
from fransys_model.vocab.tables import items

if TYPE_CHECKING:
    from pathlib import Path

    from fransys_layout.stages.types import PlacedFunction
    from fransys_model.kernel import Finding

_REACHES, _CLEARS = 32, 64
_SHEET = {
    "width_mm": 420,
    "height_mm": 297,
    "content_x_mm": 10,
    "content_y_mm": 10,
    "content_width_mm": 400,
    "frame_columns": 8,
    "frame_rows": 6,
    "module_mm": Decimal("2.5"),
}
_FOOT_MM = 86  # a content box 275 grids high: the plug rows' keep-outs end at 208, or 216 shifted


def _build(tmp: Path, row_gap: int, *, content_mm: int | None = None) -> fr.BuildResult:
    """The module K1 wired to plug J1, plug pin 2 on the 0 V rail, J1 mated to board U1.

    `content_mm` cuts the sheet's content box to that many mm high, so the rows stand at its foot.
    """
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    sheet = None
    if content_mm is not None:
        sheet = d.layout.sheet("Short", **{**_SHEET, "content_height_mm": content_mm})
    d.layout.profile(row_gap=row_gap, sheet=sheet)
    with d.function("G", "Group"):
        psu = d.device("T1", "DEMO-PSU-24")
        module = d.device("K1", "DEMO-PLC-DO-2")
        plug = d.device("J1", "DEMO-CONN-2P")
        board = d.device("U1", "DEMO-IO-2X")
    d.ac_supply("MAINS", 230, psu.input["L"], n=psu.input["N"])
    d.dc_supply("S", psu)
    d.wire(module.do_1["1"], plug.x1["1"], wire=(BU, 0.5))
    d.wire(psu.output["-"], plug.x1["2"], wire=(BU, 0.5))
    d.mate(plug, board.x1)
    cover = tmp / "cabinet.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover))


def _laid_out(result: fr.BuildResult, *, rule: bool) -> tuple[Any, tuple[Finding, ...]]:
    """The stages and findings of `result`'s model, laid out with the rule or without it."""
    with pytest.MonkeyPatch.context() as patch:
        if not rule:
            patch.setattr(stack_room, "clear_symbols", lambda *_, **__: None)
        return stage_results(result.model, read_inputs(result.model))


def _placed(result: fr.BuildResult, *, rule: bool) -> tuple[PlacedFunction, ...]:
    """The placed functions of `result`'s model, laid out with the rule or without it."""
    return _laid_out(result, rule=rule)[0].layout.placed


@pytest.fixture(scope="module")
def builds(tmp_path_factory: pytest.TempPathFactory) -> dict[int, fr.BuildResult]:
    """One build per row gap, shared by the module's tests."""
    tmp = tmp_path_factory.mktemp("symbol_row")
    return {gap: _build(tmp, gap) for gap in (_REACHES, _CLEARS)}


def _pins(placed: tuple[PlacedFunction, ...], orientation: Orientation) -> list[PlacedFunction]:
    """The contact cells turned `orientation`, left to right: R0 the plug's, R180 the board's."""
    found = (p for p in placed if p.geometry.key == "contact-male")
    return sorted((p for p in found if p.geometry.orientation is orientation), key=lambda p: p.at.x)


def _port_ys(pins: list[PlacedFunction]) -> set[int]:
    """The page y of every port of `pins`."""
    return {p.at.y + g.at.y for p in pins for g in p.geometry.ports}


def _ground_body(result: fr.BuildResult) -> Box:
    """The page box of the plug's ground body (the one ground not on the PSU)."""
    (one,) = (s for s in layout_of(result.model, PowerSymbol).values() if "x1" in s.key)
    geometry = symbol_geometry(one.symbol, orientation=Orientation[one.orientation.name])
    return translate(geometry.body, dx=one.x, dy=one.y)


def test_a_ground_pointing_up_moves_its_whole_pin_row(builds) -> None:
    """N-case: the ground clears the box it faces, and both plug pins keep one port y."""
    result = builds[_REACHES]
    assert POWER_SYMBOL_UNPLACED not in {f.code for f in fr.check(result)}
    placed = _placed(result, rule=True)
    (k1,) = (one.id for one in items(result.model).values() if one.tag == "K1")
    (box,) = (p for p in placed if p.function == k1)
    k = placed_keepout(box)
    assert _ground_body(result).y > k.y + k.height
    assert len(_port_ys(_pins(placed, Orientation.R0))) == 1


def test_the_mated_row_moves_with_its_pin_row(builds) -> None:
    """The plug's row and the board's mated row drop by one delta and still touch."""
    result = builds[_REACHES]
    with_rule, without = _placed(result, rule=True), _placed(result, rule=False)
    for orientation in (Orientation.R0, Orientation.R180):
        moved = {
            a.at.y - b.at.y
            for a, b in zip(_pins(with_rule, orientation), _pins(without, orientation), strict=True)
        }
        assert moved == {8}
    for host, face in zip(
        _pins(with_rule, Orientation.R0), _pins(with_rule, Orientation.R180), strict=True
    ):
        assert (
            host.at.y + host.geometry.body.y + host.geometry.body.height
            == face.at.y + face.geometry.body.y
        )


def test_a_symbol_that_does_not_reach_moves_nothing(builds) -> None:
    """At a row gap the lead clears, every function stands where it stands without the rule."""
    result = builds[_CLEARS]
    assert _ground_body(result)  # the plug's ground is drawn: the case is not empty
    with_rule, without = _placed(result, rule=True), _placed(result, rule=False)
    assert [(p.function, p.at) for p in with_rule] == [(p.function, p.at) for p in without]


def test_a_shifted_row_over_the_page_foot_is_reported_not_moved(tmp_path: Path) -> None:
    """N-case: the shift pushes the plug rows past the content box foot; `PAGE_OVERFULL` says so.

    No page move happens (the whole-box move reads width only), and without the rule the same
    sheet is not overfull: the shift alone causes the finding.
    """
    result = _build(tmp_path, _REACHES, content_mm=_FOOT_MM)
    stages, findings = _laid_out(result, rule=True)
    assert {p.page for p in stages.layout.placed} == {1}
    (over,) = (f for f in findings if f.code == "PAGE_OVERFULL")
    pins = [p for p in stages.layout.placed if p.geometry.key == "contact-male"]
    lowest = max(p.at.y for p in pins)  # only the shifted-down row crosses the foot
    assert set(over.subjects) == {p.function for p in pins if p.at.y == lowest}
    _, bare = _laid_out(result, rule=False)
    assert "PAGE_OVERFULL" not in {f.code for f in bare}
