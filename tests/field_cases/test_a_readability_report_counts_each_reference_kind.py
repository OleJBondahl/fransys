"""Field case: the readability report counts a page's references by kind, and is stable.

The engineering shape: one cabinet page holds a relay whose coil is drawn with a contact image
that lists its one wired contact, a net of three lamp ends drawn as a star with one branch, and a
connector pin wired to a connector on the next page, so the wire is cut into a marker pair.

The need: a reader judging the printed pages asked for the references of each page by kind, so
that a page full of one-target references can be told from one that sends the reader far.
`fr.readability(result)` returns one row for each page and one for each unit; this page's row
counts one contact image (one contact), one star (one branch) and one page cut.
The rule (decision 0182): the report is a Fransys function over the laid-out model; same model,
same rows; the cut of a two-port net is its own kind and is never counted as a star.
"""

import tempfile
from pathlib import Path

import fransys as fr
from fransys.colours import BU


def _build() -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    d.project(title="Readability", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-12", text="First issue", created="XX")
    cabinet = d.location("CAB", "Cabinet")
    with d.function("A", "Group A"):
        k1 = d.device("K1", "DEMO-RLY-2CO-24")
        feed = d.terminal_strip("X1", "DEMO-TB-2.5")
        h1, h2, h3 = (d.device(f"H{n}", "DEMO-LAMP-24") for n in (1, 2, 3))
        j1 = d.device("J1", "DEMO-CONN-2P")
    with d.function("B", "Group B") as second:
        j2 = d.device("J2", "DEMO-CONN-2P")
    wire = (BU, 0.75)
    d.detail.wire(feed.run("L", 1)[1], k1.coil["A1"], wire=wire)
    d.detail.wire(k1.co_1["11"], feed.run("M", 1)[1], wire=wire)
    d.detail.wire(k1.co_1["14"], h1.lamp["1"], wire=wire)
    d.detail.wire(h1.lamp["2"], h2.lamp["2"], wire=wire)
    d.detail.wire(h1.lamp["2"], h3.lamp["2"], wire=wire)
    d.detail.wire(k1.coil["A2"], h2.lamp["1"], wire=wire)
    d.detail.wire(j1.x1["2"], j2.x1["2"], wire=wire)
    d.layout.break_before(second)
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Readability\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cabinet, cover=cover))


def _counts(row: fr.derive.ReadabilityPage) -> dict[str, int]:
    return {
        "contact_images": row.contact_images,
        "contact_image_targets": row.contact_image_targets,
        "single_contact_images": row.single_contact_images,
        "stars": row.stars,
        "star_branches": row.star_branches,
        "single_branch_stars": row.single_branch_stars,
        "page_cuts": row.page_cuts,
    }


def test_the_page_with_all_three_kinds_counts_each_as_one() -> None:
    first, _ = fr.readability(_build()).pages
    assert _counts(first) == {
        "contact_images": 1,
        "contact_image_targets": 1,
        "single_contact_images": 1,
        "stars": 1,
        "star_branches": 1,
        "single_branch_stars": 1,
        "page_cuts": 1,
    }


def test_the_second_page_holds_only_the_other_end_of_the_cut() -> None:
    _, second = fr.readability(_build()).pages
    assert (second.drawing_set, second.number) == (1, 2)
    assert _counts(second) == dict.fromkeys(_counts(second), 0) | {"page_cuts": 1}


def test_the_unit_row_adds_its_pages_up() -> None:
    report = fr.readability(_build())
    (unit,) = report.units
    assert unit.unit is None
    assert unit.pages == 2
    assert unit.page_cuts == 2
    assert unit.fill_percent == min(row.fill_percent for row in report.pages)


def test_two_builds_of_one_model_give_equal_rows() -> None:
    first, second = _build(), _build()
    assert fr.readability(first) == fr.readability(second)
    assert fr.readability(first) == fr.readability(first)
