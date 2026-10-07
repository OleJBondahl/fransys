"""A two-cable harness through the facade (CT5-4 P3, CD9, CD-H3): one dashed block in the export.

One SYSTEM document, harness `WH1` of cables `W1` and `W2` sharing one motor end (`demo_parts`).
The write runs once and is shared by the tests.
"""

import functools

import fransys as fr
import fransys_author
import pytest
from _model_build_cover import _COVER
from fransys_render import cable_blocks

from fransys_layout import lay_out_cables
from fransys_model.derive import printed_designation
from fransys_model.derive.cable_drawing import cable_block_key
from fransys_model.vocab import DocumentPreset
from fransys_model.vocab.tables import items, units


def _built():
    parts = fr.parts("demo_parts")
    d = fransys_author.Design(parts)
    d.project(title="Harness drawings", number="DEMO-6", customer="Demo Co", revision=1, author="d")
    d.revision(1, date="2026-10-07", text="First issue", created="XX")
    loc, grp = d.location("C1", "Demo cabinet"), d.group("SUP", "Supply")
    harness = d.harness(tag="WH1", at=loc, group=grp)
    m1, m2, m3 = (
        d.item("DEMO-MOTOR-4KW", tag=f"M{n}", parent=harness, at=loc, group=grp) for n in (1, 2, 3)
    )
    d.cable("DEMO-CBL-4G1.5", tag="W1", parent=harness, at=loc, length_mm=5000).core(
        1, m1["U"], m2["U"]
    )
    d.cable("DEMO-CBL-4G1.5", tag="W2", parent=harness, at=loc).core(1, m1["V"], m3["U"])
    return fr.build(parts, d.draft(), fr.document(DocumentPreset.SYSTEM, None, cover=_COVER))


@pytest.fixture(scope="module")
def written(tmp_path_factory):
    """`(out files, intermediates dir, built)` of one write, run on first call inside a test."""

    def run():
        work = tmp_path_factory.mktemp("harness")
        built = _built()
        return fr.write(built, work / "out", intermediates=work / "inter"), work / "inter", built

    return functools.cache(run)


def test_a_two_cable_harness_writes_one_block_with_a_dashed_box(written):
    """CD9 through `fr.write`: one block SVG, the harness label and both headings in it, in a PDF.

    The block is in the "No part number" run (CD-H3). Probe: the engine's `drawable` refusing
    a harness block (the write then raises).
    """
    paths, inter, built = written()
    assert any(p.suffix == ".pdf" for p in paths)
    (source,) = [p.read_text(encoding="utf-8") for p in sorted(inter.glob("*.typ"))]
    assert source.count('format: "svg"') == 1
    assert "stroke-dasharray" in source  # the harness box (and nothing else is dashed here)
    for text in ("-WH1", "-WH1-W1, 5000 mm", "-WH1-W2"):
        assert text in source, text
    assert "No part number" in source
    (harness,) = [i.id for i in items(built.model).values() if i.key == ("WH1",)]
    assert cable_block_key(None, harness)


def _unit_harness():
    """A harness `WH1` of two cables inside a unit: its block exists absolutely and in the unit."""
    parts = fr.parts("demo_parts")
    d = fransys_author.Design(parts)
    d.project(title="Unit harness", number="DEMO-8", customer="Demo Co", revision=1, author="d")
    d.revision(1, date="2026-10-07", text="First issue", created="XX")
    cab = d.scope("cab").unit("demo-pump-cabinet", revision=1, interface="1")
    cab.revision(1, date="2026-01-01", text="First release", created="XX")
    loc, grp = cab.location("C1", "Cabinet"), cab.group("G1", "Group")
    harness = cab.harness(tag="WH1", at=loc, group=grp)
    m1, m2, m3 = (
        cab.item("DEMO-MOTOR-4KW", tag=f"M{n}", parent=harness, at=loc, group=grp)
        for n in (1, 2, 3)
    )
    cab.cable("DEMO-CBL-4G1.5", tag="W1", parent=harness, at=loc).core(1, m1["U"], m2["U"])
    cab.cable("DEMO-CBL-4G1.5", tag="W2", parent=harness, at=loc).core(1, m1["V"], m3["U"])
    return parts, d


def test_the_harness_label_is_its_printed_designation_in_every_reading():
    """CD7, acceptance 22: the label is `-WH1`, as `printed_designation` gives, in both readings.

    Probe: label with `item_designation`, which has no dash.
    """
    parts, d = _unit_harness()
    frozen = fr.build(parts, d.draft()).model
    model, _ = lay_out_cables(frozen)
    svgs = cable_blocks(model)
    (harness,) = [i.id for i in items(frozen).values() if i.key[-1] == "WH1"]
    (unit,) = list(units(frozen))
    absolute, inside = (printed_designation(frozen, harness, unit=u) for u in (None, unit))
    assert absolute.startswith("-")
    for reading, label in ((None, absolute), (unit, inside)):
        text = svgs[cable_block_key(reading, harness)]
        assert f">{label}<" in text, (reading, label)


def _nested_unit_harness():
    """A harness `WH1` of two cables in unit `B1`, which sits inside unit `A1` (a nested root)."""
    parts = fr.parts("demo_parts")
    d = fransys_author.Design(parts)
    d.project(title="Nested harness", number="DEMO-9", customer="Demo Co", revision=1, author="d")
    d.revision(1, date="2026-10-07", text="First issue", created="XX")
    outer = d.scope("out").unit("demo-pump-cabinet", revision=1, interface="1", tag="A1")
    outer.revision(1, date="2026-01-01", text="First release", created="XX")
    cab = outer.scope("sub").unit(
        "demo-pump-cabinet", version=2, revision=1, interface="1", tag="B1"
    )
    cab.revision(1, date="2026-01-01", text="First release", created="XX")
    loc, grp = cab.location("C1", "Cabinet"), cab.group("G1", "Group")
    harness = cab.harness(tag="WH1", at=loc, group=grp)
    m1, m2, m3 = (
        cab.item("DEMO-MOTOR-4KW", tag=f"M{n}", parent=harness, at=loc, group=grp)
        for n in (1, 2, 3)
    )
    cab.cable("DEMO-CBL-4G1.5", tag="W1", parent=harness, at=loc).core(1, m1["U"], m2["U"])
    cab.cable("DEMO-CBL-4G1.5", tag="W2", parent=harness, at=loc).core(1, m1["V"], m3["U"])
    return parts, d


def test_the_harness_label_in_a_nested_units_reading_drops_the_root_as_the_headings_do():
    """CD7, acceptance 22: in unit `B1`'s own reading the label is `-WH1`, absolutely `-A1-B1-WH1`.

    Probe: render's label call without `unit=`, which prints the absolute label in every reading.
    """
    parts, d = _nested_unit_harness()
    frozen = fr.build(parts, d.draft()).model
    model, _ = lay_out_cables(frozen)
    svgs = cable_blocks(model)
    (harness,) = [i.id for i in items(frozen).values() if i.key[-1] == "WH1"]
    (unit,) = [u for u, r in units(frozen).items() if r.key == ("out", "sub", "unit")]
    inside, absolute = svgs[cable_block_key(unit, harness)], svgs[cable_block_key(None, harness)]
    assert ">-WH1<" in inside
    assert ">-WH1-W1<" in inside  # the heading's prefix is the label
    assert ">-A1-B1-WH1<" not in inside
    assert ">-A1-B1-WH1<" in absolute
    assert ">-A1-B1-WH1-W1<" in absolute
