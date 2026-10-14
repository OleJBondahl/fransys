"""A bar's end in a cable block draws the protective-earth symbol: no box, no label, no pin text.

One cabinet unit: a lamp and a terminal strip joined by one cable whose screen core lands on a
PE bar (`demo_parts`). The solid ends keep their boxes beside it (layout-0219).
"""

import re
from typing import Any, NamedTuple

import fransys as fr
import pytest
from fransys_render import cable_blocks

from fransys_layout import lay_out_cables

_EARTH = 'class="symbol earth"'
_RECT = re.compile(r'<rect class="symbol end-box"')
_TEXT = re.compile(r'<text class="label end-label"[^>]*>([^<]*)</text>')


class _Unit(NamedTuple):
    """A unit with no interface to hand back."""


@fr.unit("pe-end", revision=1, interface_version=1, date="2026-10-14", text="first", by="AB")
def _unit(c: Any) -> _Unit:
    x1 = c.terminal_strip("X1", "DEMO-TB-2.5", 4)
    h1 = c.device("H1", "DEMO-LAMP-24")
    pe1 = c.device("PE1", "DEMO-PEBAR-20").pe
    w2 = c.cable("W2", "DEMO-CBL-2X2X0.75-SP", length_m=25)
    w2.core(1, x1[2], h1[2])
    w2.core(5, pe1)
    w2.spare()
    return _Unit()


@pytest.fixture(scope="module")
def blocks(tmp_path_factory: pytest.TempPathFactory) -> list[str]:
    folder = tmp_path_factory.mktemp("pe-end")
    cover = folder / "cover.md"
    cover.write_text("# C\n", encoding="utf-8")
    d = fr.design("demo_parts")
    d.add(_unit, "U1")
    pages = (fr.PageKind.HARNESS_DRAWING, fr.PageKind.CABLE_LIST)
    preset = fr.DocumentPreset.CABINET_SCHEMATIC
    built = fr.build(d, fr.document(preset, "pe-end", cover=cover, add=pages))
    svgs = dict(cable_blocks(lay_out_cables(built.model)[0])).values()
    return [s for s in svgs if _EARTH in s]


def test_the_bar_end_draws_one_earth_symbol_and_no_box_or_label(blocks: list[str]) -> None:
    """Each block with the bar end has one symbol; the solid ends keep box and label (control)."""
    assert blocks
    for svg in blocks:
        assert svg.count(_EARTH) == 1
        assert len(_RECT.findall(svg)) == 2  # -H1 and -X1 only, none for -PE1
        labels = _TEXT.findall(svg)
        assert labels
        assert not [t for t in labels if "PE1" in t]
        assert svg.count('class="label pin"') == 2  # the bar end prints no pin text


_MOVE = re.compile(
    r'class="symbol earth" transform="translate\(([\d.]+),([\d.]+)\)">(.*?)</g>\s*</g>', re.DOTALL
)
_TOP_BOX = re.compile(
    r'<rect class="symbol end-box" x="[\d.]+" y="([\d.]+)" width="[\d.]+" height="([\d.]+)"'
)
_Y = re.compile(r'y[12]="(-?[\d.]+)"')


def test_the_top_end_symbol_stands_above_the_core_with_its_lead_on_the_core(
    blocks: list[str],
) -> None:
    """The bar lands on the top row: the lead ends on the end band's lower edge, bars above it."""
    for svg in blocks:
        ((_, y, body),) = _MOVE.findall(svg)
        band = min((float(a), float(b)) for a, b in _TOP_BOX.findall(svg))  # the top end box
        ys = [float(v) for v in _Y.findall(body)]
        assert float(y) + max(ys) == band[0] + band[1]  # the port sits on the core's start
        assert min(ys) < 0  # the bars stand above the origin: the symbol points up
