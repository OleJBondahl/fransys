"""Field case: every reference of one net takes the same fill, on every page.
The bug: none; a reader asked for one net's references to share a colour across the whole PDF.
Fixed by render-0013 (REF-COLOURS C1 and C2): a reference's fill is its net's tint, `(#n - 1) mod 8`."""

import re
import tempfile
from pathlib import Path

import fransys as fr
import pytest
from _drawn_pages import drawn_pages, markers_in, ref_texts
from fransys.colours import BU

_NUMBER = re.compile(r"#(\d+)")


@pytest.fixture(scope="module")
def tags() -> list[tuple[str, str]]:
    """(net number, tint) of every numbered reference marker the pages draw, in page order."""
    root = Path(tempfile.mkdtemp())
    d = fr.design("demo_parts", place="CAB")
    d.project(title="Tints", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-15", text="First issue", created="XX")
    cabinet = d.location("CAB", "Cabinet")
    with d.function("A", "Group A"):
        j1 = d.device("J1", "DEMO-CONN-2P")
    with d.function("B", "Group B"):
        j2 = d.device("J2", "DEMO-CONN-2P")
    with d.function("C", "Group C"):
        j3 = d.device("J3", "DEMO-CONN-2P")
    wire = (BU, 0.75)
    d.series(j1.x1["2"], j2.x1["2"], wire=wire)
    d.series(j2.x1["2"], j3.x1["2"], wire=wire)
    d.series(j1.x1["1"], j2.x1["1"], wire=wire)
    (root / "cover.md").write_text("# Tints\n", encoding="utf-8")
    result = fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cabinet, cover=root / "cover.md"))
    assert [f.code for f in result.findings if f.severity.name == "ERROR"] == []
    return [
        (m[1], str(marker.tint or ""))
        for drawing in drawn_pages(result.model).values()
        for marker in markers_in(drawing)
        if (m := _NUMBER.search(" ".join(ref_texts(marker))))
    ]


@pytest.mark.rule("REFERENCE-TINTS")
def test_a_net_on_three_pages_has_one_fill_on_all_of_them(tags: list[tuple[str, str]]) -> None:
    assert tags, "no numbered reference marker is drawn for this input: the fixture no longer cuts a net across pages"
    by_net: dict[str, set[str]] = {}
    for number, style in tags:
        by_net.setdefault(number, set()).add(style)
    assert max(len([1 for n, _ in tags if n == k]) for k in by_net) >= 3
    assert all(len(styles) == 1 and "" not in styles for styles in by_net.values())


@pytest.mark.rule("REFERENCE-TINTS")
def test_neighbouring_nets_have_different_fills(tags: list[tuple[str, str]]) -> None:
    """Acceptance 2: links #1 and #2 are neighbours and show different tints."""
    fill = dict(tags)
    assert {"1", "2"} <= fill.keys(), f"links #1 and #2 are not both drawn as numbered markers (have {sorted(fill)})"
    assert fill["1"] != fill["2"]
