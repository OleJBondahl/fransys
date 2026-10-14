"""The find box lists units beside items (overview-0007)."""

import re

from fransys_overview._js_panels import JS_PANELS


def test_the_search_reads_the_unit_labels() -> None:
    body = re.search(r"const hitsFor = .*?\n};", JS_PANELS, re.DOTALL)
    assert body is not None
    assert "data.units" in body.group(0)
