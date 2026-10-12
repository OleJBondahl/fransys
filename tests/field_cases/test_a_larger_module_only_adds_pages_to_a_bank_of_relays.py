"""Field case: a larger sheet module turns a clean bank of relays into off-page boxes.

The engineering shape: one unit holds N relays side by side in their own functions. Each coil is
fed from an interface strip and a pin of an external controller, and each relay switches a lamp
whose return runs to a second strip. All coils are poles of one item and kind with one wiring
signature, so they bundle into ONE column of N lanes. The same design is built at the house module
and at a sheet whose only difference is `module_mm=3.0` (a coarser grid: fewer grid units
across the same millimetres).

The bug: at the larger module N=8 and N=9 give `OUT_OF_CONTENT_BOX` where the house module gives
none, and the house module does too from N=10. A larger module should only lower the page's
capacity, and layout should add pages (owner 2026-10-08, "cut first"). The coil bundle is one
column wider than the content box (about 1127 grid units against 1093 at N=8): partition never
split one column (layout-0011) and `pack` let it stand alone on a page, so its last lanes' boxes
and contact tables left the box.

The fix, decision layout-0182: at re-plan a column measured wider than the content box is cut
between its lanes, fill first, and the rest continues as the next column.
"""

import contextlib
import tempfile
from decimal import Decimal
from functools import cache
from pathlib import Path
from typing import NamedTuple

import fransys as fr
import pytest

from fransys_model.layout import Page, layout_of


class _Io(NamedTuple):
    feed: fr.TerminalStrip


_CODE = "OUT_OF_CONTENT_BOX"
_PINS = tuple(f"CH{j:02d}-" for j in range(1, 17))
_SHEET = {
    "width_mm": 420,
    "height_mm": 297,
    "content_x_mm": 10,
    "content_y_mm": 10,
    "content_width_mm": 400,
    "content_height_mm": 277,
    "frame_columns": 8,
    "frame_rows": 6,
}


def _bank(module: str | None, count: int, *, one_group: bool = False, lean: bool = False):
    @fr.unit("demo-bank", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
    def bank(u: fr.Design) -> _Io:
        if module is not None:
            sheet = u.layout.sheet("S3", **_SHEET, module_mm=Decimal(module))
            u.layout.profile(sheet=sheet)
        feed = u.terminal_strip("X1", "DEMO-TB-2.5", 8, interface=True)
        back = u.terminal_strip("X2", "DEMO-TB-2.5", 8)
        with u.function("PLC", "Controller"):
            controller = u.device("A1", None, pins=_PINS, external=True)
        shared = u.function("R", "Relays") if one_group else contextlib.nullcontext()
        with shared:
            for i in range(count):
                own = (
                    contextlib.nullcontext()
                    if one_group
                    else u.function(f"R{i + 1}", f"Relay {i + 1}")
                )
                with own:
                    relay = u.device(f"K{i + 1}", "DEMO-RLY-2CO-24")
                    u.wire(feed[1 + i % 4], relay.coil["A1"], wire=("WH", 0.75))
                    u.wire(controller[_PINS[i % 16]], relay.coil["A2"], wire=("BU", 0.75))
                    if lean:
                        continue
                    lamp = u.device(f"P{i + 1}", "DEMO-LAMP-24")
                    u.wire(relay.co_1["14"], lamp.lamp[1], wire=("WH", 0.75))
                    u.wire(back[1 + i % 6], relay.co_1["11"], wire=("WH", 0.75))
                    u.wire(lamp.lamp[2], back[7], wire=("BU", 0.75))
        return _Io(feed)

    return bank


@cache
def _built(
    module: str | None, count: int, *, one_group: bool = False, lean: bool = False
) -> fr.BuildResult:
    """Built in the tests' bodies, so a build error is a test FAILURE, not a fixture error."""
    with tempfile.TemporaryDirectory() as tmp:
        cover = Path(tmp) / "cover.md"
        cover.write_text("# Bank\n", encoding="utf-8")
        d = fr.design("demo_parts")
        d.add(_bank(module, count, one_group=one_group, lean=lean), "U1")
        document = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-bank", cover=cover)
        return fr.build(d, document)


def _codes(
    module: str | None, count: int, *, one_group: bool = False, lean: bool = False
) -> list[str]:
    return [f.code for f in fr.check(_built(module, count, one_group=one_group, lean=lean))]


def _off_page(module: str | None, count: int) -> int:
    return _codes(module, count).count(_CODE)


def _pages(module: str | None, count: int) -> int:
    return len(layout_of(_built(module, count).model, Page))


@pytest.mark.parametrize("count", [8, 9])
def test_the_house_module_draws_the_bank_inside_the_content_box(count: int) -> None:
    """The control: the same bank at the house module has no box off the page."""
    assert _off_page(None, count) == 0


@pytest.mark.parametrize("count", [8, 9])
def test_a_larger_module_leaves_no_box_off_the_page(count: int) -> None:
    """The coarser module lowers the page's capacity; layout cuts, it draws nothing outside."""
    assert _off_page("3.0", count) == 0


def test_a_bank_wider_than_the_house_page_leaves_no_box_off_the_page() -> None:
    """Ten relays outgrow the house module's page too; the bundle is cut, nothing leaves it."""
    assert _off_page(None, 10) == 0


@pytest.mark.parametrize("count", [8, 9])
def test_a_larger_module_adds_pages(count: int) -> None:
    """The coarser module lowers capacity, so the same bank takes more pages."""
    assert _pages("3.0", count) > _pages(None, count)


def test_a_bank_inside_one_function_still_reports_the_group_split() -> None:
    """The cut gives no finding, but a function wider than a page is split and says so."""
    codes = _codes("3.0", 8, one_group=True)
    assert codes.count(_CODE) == 0
    assert codes.count("GROUP_SPLIT") == 1


def test_a_bank_that_is_wide_only_by_its_bundle_gets_no_finding_from_the_cut() -> None:
    """One function wide only by its coil bundle: the cut (layout-0182) splits no group."""
    codes = _codes("3.0", 8, one_group=True, lean=True)
    assert codes.count(_CODE) == 0
    assert codes.count("GROUP_SPLIT") == 0
