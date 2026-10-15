"""Field case: every reference of one net takes the same fill, on every page (render-0013).

The engineering shape: three connectors, each in its own function block on its own page
(`break_before`), joined by one net, so the net is referenced on three pages. A second, separate
net runs between the first two connectors.

The need: a reader looking for the other ends of a net asked for its references to share a
colour across the whole PDF, "an intuitive helper" beside the unchanged text.
The rule (decision render-0013, REF-COLOURS C1 and C2): a reference's pentagon is filled with
the tint of its net's slot, `(#n - 1) mod 8`, so every reference of one `#n` has one fill and
neighbouring nets differ.
"""

import re
import tempfile
from pathlib import Path

import fransys as fr
import pytest
from fransys.colours import BU

_TAG = re.compile(r'<polyline class="marker" points="[^"]*"( style="[^"]*")?/><text[^>]*>#(\d+)')


@pytest.fixture(scope="module")
def tags() -> list[tuple[str, str]]:
    """(net number, fill style) of every reference on every page, in page order."""
    root = Path(tempfile.mkdtemp())
    d = fr.design("demo_parts", place="CAB")
    d.project(title="Tints", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-15", text="First issue", created="XX")
    cabinet = d.location("CAB", "Cabinet")
    with d.function("A", "Group A"):
        j1 = d.device("J1", "DEMO-CONN-2P")
    with d.function("B", "Group B") as second:
        j2 = d.device("J2", "DEMO-CONN-2P")
    with d.function("C", "Group C") as third:
        j3 = d.device("J3", "DEMO-CONN-2P")
    wire = (BU, 0.75)
    d.detail.wire(j1.x1["2"], j2.x1["2"], wire=wire)
    d.detail.wire(j2.x1["2"], j3.x1["2"], wire=wire)
    d.detail.wire(j1.x1["1"], j2.x1["1"], wire=wire)
    d.layout.break_before(second)
    d.layout.break_before(third)
    (root / "cover.md").write_text("# Tints\n", encoding="utf-8")
    result = fr.build(
        d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cabinet, cover=root / "cover.md")
    )
    assert [f.code for f in result.findings if f.severity.name == "ERROR"] == []
    fr.write(result, root / "out", intermediates=root / "inter")
    found = []
    for svg in sorted((root / "inter").glob("layout.page-*.svg")):
        found += [(num, style) for style, num in _TAG.findall(svg.read_text("utf-8"))]
    return found


def test_a_net_on_three_pages_has_one_fill_on_all_of_them(tags: list[tuple[str, str]]) -> None:
    by_net: dict[str, set[str]] = {}
    for number, style in tags:
        by_net.setdefault(number, set()).add(style)
    assert max(len([1 for n, _ in tags if n == k]) for k in by_net) >= 3
    assert all(len(styles) == 1 and "" not in styles for styles in by_net.values())


def test_neighbouring_nets_have_different_fills(tags: list[tuple[str, str]]) -> None:
    """Acceptance 2: links #1 and #2 are neighbours and show different tints."""
    fill = dict(tags)
    assert fill["1"] != fill["2"]
