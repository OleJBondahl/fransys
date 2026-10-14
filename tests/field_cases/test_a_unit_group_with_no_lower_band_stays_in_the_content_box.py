"""Field case: a unit group with no lower band to cut still overflows its page.

The engineering shape: a board unit offers a header; one loom's plug mates it and runs to two
contactors' lead housings, and a chain of contactor coils in series hangs from one housing. The
group's upper band is two or six coils tall and there are no further looms, so no lower band
exists below the outline to cut at.

The bug: the tall-group cut (decision layout-0167) cuts at the outline's top edge and so needs
a lower band; with none it cuts nothing, the page grows past the content box and reports
OUT_OF_CONTENT_BOX and PAGE_OVERFULL, with the line's ink outside the box. The fallback is its own
order (TALL-PAGE R4, held). CLEANUP-ROUND-2 CL8 holds the row.
"""

import sys
from pathlib import Path

import pytest
lazy import fransys as fr

sys.path.insert(0, str(Path(__file__).parent))  # the sibling case whose tall group this reuses
from test_a_harness_line_on_an_overfull_page_still_routes import _built

from fransys_model.layout import Page, layout_of

_HELD = "CL8: a group with no lower band overflows its page (TALL-PAGE R4 held)"
_OVER = {"OUT_OF_CONTENT_BOX", "PAGE_OVERFULL"}


def _drawn(built: fr.BuildResult) -> None:
    assert [f for f in built.findings if f.severity.name == "ERROR"] == []
    assert len(layout_of(built.model, Page)) >= 2


@pytest.mark.xfail(strict=True, reason=_HELD)
@pytest.mark.parametrize("deep", [2, 6])
def test_a_tall_upper_band_with_no_lower_band_stays_inside_the_content_box(deep: int) -> None:
    built = _built(2, 0, deep, looms=False)
    _drawn(built)
    assert not _OVER & {f.code for f in built.findings}
