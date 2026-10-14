"""Field case: a unit group with no lower band to cut still overflows its page.

The engineering shape: a board unit offers a header; one loom's plug mates it and runs to two
contactors' lead housings, and a chain of contactor coils in series hangs from one housing. The
group's upper band is two or six coils tall and there are no further looms, so no lower band
exists below the outline to cut at.

The bug: the tall-group cut (decision layout-0167) cuts at the outline's top edge and so needs
a lower band; with none it cuts nothing, the page grows past the content box and reports
OUT_OF_CONTENT_BOX and PAGE_OVERFULL, with the line's ink outside the box.
The fix (decision layout-0234): such a group hands its shortest upper column down to stand
below the outline on the next page, so the outline leaves the first page. The six-coil chain is
taller than the page by itself (T4), so it stays held.
"""

import sys
from pathlib import Path

import pytest
lazy import fransys as fr

sys.path.insert(0, str(Path(__file__).parent))  # the sibling case whose tall group this reuses
from test_a_harness_line_on_an_overfull_page_still_routes import _built

from fransys_model.layout import Outline, Page, SymbolPlacement, layout_of

_HELD = "CL8: the upper band alone is taller than the page (TALL-PAGE T4: held)"
_OVER = {"OUT_OF_CONTENT_BOX", "PAGE_OVERFULL"}


def _drawn(built: fr.BuildResult) -> None:
    assert [f for f in built.findings if f.severity.name == "ERROR"] == []
    assert len(layout_of(built.model, Page)) >= 2


def test_a_tall_upper_band_with_no_lower_band_stays_inside_the_content_box() -> None:
    built = _built(2, 0, 2, looms=False)
    _drawn(built)
    assert not _OVER & {f.code for f in built.findings}
    (outline,) = layout_of(built.model, Outline).values()
    column = [
        one for one in layout_of(built.model, SymbolPlacement).values() if one.page == outline.page
    ]
    assert column, "the outline's page carries the column handed down"


@pytest.mark.xfail(strict=True, reason=_HELD)
def test_an_upper_band_taller_than_the_page_alone_stays_inside_the_content_box() -> None:
    built = _built(2, 0, 6, looms=False)
    _drawn(built)
    assert not _OVER & {f.code for f in built.findings}
