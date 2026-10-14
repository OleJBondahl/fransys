"""The Features panel opens below the toolbar, never over it (overview-0006).

The page is checked in a browser outside the gate (`internal/scripts/overview_smoke.py`); this
test holds the CSS rule that keeps the panel clear: it hangs from the header's bottom edge.
"""

import re

from fransys_overview._template import TEMPLATE


def _rule(selector: str) -> dict[str, str]:
    found = re.search(rf"(?m)^{re.escape(selector)} \{{(.*?)\}}", TEMPLATE, re.DOTALL)
    assert found is not None, selector
    return dict(re.findall(r"([\w-]+):\s*([^;]+);", found.group(1)))


def test_the_features_panel_hangs_from_the_header_bottom() -> None:
    header, features, body = _rule("header"), _rule("#features"), _rule("#feat-body")
    assert header.get("position") == "relative"
    assert features.get("position") != "relative"
    assert body["position"] == "absolute"
    assert body["top"] == "100%"
