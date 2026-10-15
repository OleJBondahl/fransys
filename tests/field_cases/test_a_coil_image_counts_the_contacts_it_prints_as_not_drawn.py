"""Field case: `fr.readability` counts the contact-image entries that print N/A.

The engineering shape: a three-pole contactor with a coil, one auxiliary contact wired and its
three main poles and a normally closed pair left unwired. Its coil's contact image lists every
contact, and a contact no conductor reaches prints `N/A` in place of a position.

The need: a reader judging the pages asked how many contacts the images list that no page draws.
`ReadabilityPage.contacts_not_drawn` and `ReadabilityUnit.contacts_not_drawn` count those entries.
It is information only: N/A is the ruled print for a contact with nothing drawn, so there is no
finding. Decision model-0258.
"""

import tempfile
from pathlib import Path

import fransys as fr
import pytest
from fransys.colours import BU

from fransys_model.derive import NO_PLACE
from fransys_model.derive.drawing_text import contact_image
from fransys_model.layout import Label, LabelKind, layout_of

_WIRE = (BU, 0.5)


@pytest.fixture(scope="module")
def built() -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    d.project(title="Spares", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-15", text="First issue", created="XX")
    cab = d.location("CAB", "Cabinet")
    psu = d.device("T1", "DEMO-PSU-24")
    q = d.device("Q1", "DEMO-CTR-3P-NC")
    lamp = d.device("P1", "DEMO-LAMP-24")
    d.detail.wire(psu.output["+"], q.coil["A1"], wire=_WIRE)
    d.detail.wire(psu.output["-"], q.coil["A2"], wire=_WIRE)
    d.detail.wire(psu.output["+"], q.aux["13"], wire=_WIRE)
    d.detail.wire(q.aux["14"], lamp["1"], wire=_WIRE)
    d.detail.wire(psu.output["-"], lamp["2"], wire=_WIRE)
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Spares\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover))


def _printed_na(result: fr.BuildResult) -> int:
    """The N/A entries the coil images print, counted from the printed texts."""
    model = result.model
    return sum(
        entry.endswith(NO_PLACE)
        for label in layout_of(model, Label).values()
        if label.kind is LabelKind.CROSS_REFERENCE and label.slot == "contacts"
        for column in contact_image(model, label)
        for entry in column
    )


def test_the_page_and_unit_rows_count_the_entries_that_print_na(built: fr.BuildResult) -> None:
    expected = _printed_na(built)
    assert expected > 0, "the case needs an image with an N/A entry"
    report = fr.readability(built)
    assert sum(row.contacts_not_drawn for row in report.pages) == expected
    assert sum(row.contacts_not_drawn for row in report.units) == expected


def test_it_raises_no_finding(built: fr.BuildResult) -> None:
    assert fr.readability(built).pages[0].contacts_not_drawn > 0
    assert not [f for f in fr.check(built) if "N/A" in f.message or "NOT_DRAWN" in f.code]
