"""Net-reference fills (render-0013, REF-COLOURS C1 and C4): `pages(model, tints)`."""

import re

import pytest
from fransys_render import pages

from fransys_model.derive.drawing_text import REF_SLOTS, reference_slot
from fransys_model.layout import LinkMarker, layout_of

TINTS = tuple(f"#{n:02x}{n:02x}ff" for n in range(1, REF_SLOTS + 1))
_PENTAGON = re.compile(r'<polyline class="marker" points="[^"]*"( style="[^"]*")?/>')


def _all_svg(model, tints=()):
    return "".join(pages(model, tints=tints).values())


def test_a_numbered_pentagon_takes_the_tint_of_its_slot(cabinet_narrow_laid_out):
    model = cabinet_narrow_laid_out
    slots = {reference_slot(model, m) for m in layout_of(model, LinkMarker).values()} - {None}
    assert slots
    fills = [style for style in _PENTAGON.findall(_all_svg(model, TINTS)) if style]
    assert fills
    assert {f' style="fill:{TINTS[s]}"' for s in slots if s is not None} >= set(fills)


def test_the_two_ends_of_one_net_share_a_fill(cabinet_narrow_laid_out):
    fills = [s for s in _PENTAGON.findall(_all_svg(cabinet_narrow_laid_out, TINTS)) if s]
    assert len(fills) == 2
    assert fills[0] == fills[1]


def test_empty_tints_give_no_fills(cabinet_narrow_laid_out):
    assert "fill:#" not in _all_svg(cabinet_narrow_laid_out)


def test_a_wrong_tint_count_raises(cabinet_narrow_laid_out):
    with pytest.raises(ValueError, match="8 tints"):
        pages(cabinet_narrow_laid_out, tints=TINTS[:7])


def test_contact_table_lines_stay_unfilled(cabinet_laid_out):
    """The wide cabinet draws contact tables (`class="marker"` lines) and no net reference."""
    svg = _all_svg(cabinet_laid_out, TINTS)
    assert svg.count('<line class="marker"') >= 2
    assert svg == _all_svg(cabinet_laid_out)
    assert "fill:#" not in svg


def test_a_stub_without_a_number_has_no_fill(cabinet_two_location_laid_out):
    """All four markers here are off stubs; any without a `#n` draws no tint."""
    model = cabinet_two_location_laid_out
    unnumbered = [
        m for m in layout_of(model, LinkMarker).values() if reference_slot(model, m) is None
    ]
    assert unnumbered
    filled = [s for s in _PENTAGON.findall(_all_svg(model, TINTS)) if s]
    assert len(filled) < len(_PENTAGON.findall(_all_svg(model, TINTS)))
