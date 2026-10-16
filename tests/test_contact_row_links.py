"""A coil's contact table links each row to the sheet where its contact is drawn (NAV-CONTACT-ROWS).

The canary design (coils on one sheet, contacts on others) gives rows on other sheets and rows on
the coil's own sheet; an invented single-sheet contactor with an unwired NC contact gives the spare
row. The rows' boxes are worked out here, from `contact_image` and the printed sizes, as the
independent oracle of `contact_rows` (CR1) and of the table geometry (CR2).
"""

import hashlib
import re
import tempfile
from dataclasses import replace
from pathlib import Path

import fransys as fr
import pytest
from fransys.colours import BU
from fransys_el import REF_TINTS
from fransys_render import pages
from test_reader_order import _design

from fransys_model.derive import page_destination, text_room_g
from fransys_model.derive.contact_image import cross_reference_text
from fransys_model.derive.contact_rows import contact_rows
from fransys_model.derive.drawing_text import CONTACT_SLOTS, contact_heading, contact_image
from fransys_model.derive.page_nav import reference_links
from fransys_model.derive.text_width import text_width
from fransys_model.layout import (
    Label,
    LabelKind,
    Page,
    layout_of,
    profile_of_page,
    sheet_format_of,
)


@pytest.fixture(scope="module")
def canary() -> fr.BuildResult:
    root = Path(tempfile.mkdtemp())
    d, cabinet = _design("a-")
    (root / "c.md").write_text("# c\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cabinet, cover=root / "c.md")
    return fr.build(d, doc)


@pytest.fixture(scope="module")
def spare() -> fr.BuildResult:
    """One contactor: a three-pole main contact, a wired NO auxiliary and an unwired NC one."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    psu = d.device("T1", "DEMO-PSU-24")
    mains = d.device("P2", "DEMO-LAMP-24")
    lamp = d.device("P1", "DEMO-LAMP-24")
    motor = d.device("M1", "DEMO-MOTOR-4KW")
    q = d.device("Q1", "DEMO-CTR-3P-NC")
    blue = (BU, 0.5)
    d.detail.wire(psu.input["L"], mains["1"], wire=blue)
    d.detail.wire(psu.input["N"], mains["2"], wire=blue)
    d.detail.wire(psu.output["+"], q.coil["A1"], wire=blue)
    d.detail.wire(psu.output["-"], q.coil["A2"], wire=blue)
    d.detail.wire(psu.output["+"], q.aux["13"], wire=blue)
    d.detail.wire(q.aux["14"], lamp["1"], wire=blue)
    d.detail.wire(psu.output["-"], lamp["2"], wire=blue)
    for pole, pin in enumerate("UVW"):
        d.detail.wire(psu.output["+"], q.main[str(2 * pole + 1)], wire=blue)
        d.detail.wire(q.main[str(2 * pole + 2)], motor.motor[pin], wire=blue)
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover))


def _tables(model) -> list[Label]:
    return [
        label
        for label in layout_of(model, Label).values()
        if label.kind is LabelKind.CROSS_REFERENCE and label.slot in CONTACT_SLOTS
    ]


def _rows(model, label: Label) -> list[tuple[str, tuple[int, int, int, int]]]:
    """(text, box) of every row of `label`'s table, worked out from the printed sizes."""
    page = layout_of(model, Page)[label.page]
    profile = profile_of_page(model, page)
    step = text_room_g(profile.text_height_mm, sheet_format_of(model, page.sheet_format).module_mm)
    pad = profile.marker_padding
    top = label.y + (step if contact_heading(model, label) else 0) + pad + step + pad
    found = []
    for column, entries in enumerate(contact_image(model, label)):
        x = label.x + pad + column * (label.width // 2)
        for index, text in enumerate(entries):
            box = (x, top + index * step, text_width(text, height=step), step)
            found.append((text, box))
    return found


def _targets(model, label: Label) -> dict[str, str]:
    """The destination of each other-sheet place a table prints, by the place text."""
    pages = layout_of(model, Page)
    return {
        cross_reference_text(model, replace(label, partners=(partner,))): page_destination(
            model, pages[partner.page]
        )
        for partner in label.partners
        if partner.page != label.page
    }


def _inside(link, label: Label) -> bool:
    return (
        label.x <= link.x
        and label.y <= link.y
        and link.x + link.width <= label.x + label.width
        and link.y + link.height <= label.y + label.height
    )


def _links(model, label: Label) -> dict[tuple[int, int, int, int], str]:
    found = reference_links(model, label.page, set(layout_of(model, Page)))
    return {(k.x, k.y, k.width, k.height): k.target for k in found if _inside(k, label)}


def test_a_row_links_to_its_contacts_sheet_and_a_same_sheet_row_has_no_link(canary) -> None:
    model = canary.model
    other = same = 0
    for label in _tables(model):
        targets = _targets(model, label)
        want = {}
        for text, box in _rows(model, label):
            place = text.split(" ", 1)[1]
            if place in targets:
                want[box] = targets[place]
                other += 1
            else:
                same += 1
        assert _links(model, label) == want
    assert other > 0 < same  # the canary holds both kinds of row


def test_a_spare_row_and_a_row_on_the_coils_own_sheet_get_no_link_and_others_do(
    spare,
) -> None:
    model = spare.model
    (label,) = [t for t in _tables(model) if "21-22 N/A" in contact_image(model, t)[1]]
    assert _links(model, label) == {}


def test_the_last_row_ends_one_padding_above_the_tables_foot(canary, spare) -> None:
    """The table's height is its rows' extent plus one padding (CR2: layout and render agree)."""
    for built in (canary, spare):
        model = built.model
        for label in _tables(model):
            page = layout_of(model, Page)[label.page]
            pad = profile_of_page(model, page).marker_padding
            rows = _rows(model, label)
            assert max(y + h for _, (_, y, _, h) in rows) + pad == label.y + label.height
            assert all(label.x <= x and x + w <= label.x + label.width for _, (x, _, w, _) in rows)


_ELEMENT = re.compile(r"<text [^>]*>[^<]*</text>|<line [^>]*/>")
# The sha256 of every page's `<text>` and `<line>` elements, taken before the rows moved into
# derive (CR3): a shifted row, heading or rule changes it. A render change elsewhere moves it too.
PINS = {
    # Re-pinned for layout-0218: the canary's box B1 gained a lamp P1 across two pins, since a
    # box with nothing connected is no longer drawn.
    # Re-pinned for model-0220: terminal X1:1 is wired to every circuit's Q coil, so it is drawn
    # as a copy at each pin and the reference markers are gone. Re-pinned again after merging
    # main (model-0235 and layout-0235 moved the same canary).
    "canary": "bad8c11998a6e0bab1e164f6fae0198975313f3f9996b57396c8aecac6b71d43",
    # Re-pinned for layout-0264: supply T1's pins print in marking order, `+ -`, no longer by
    # their partners' x; its two markers swap places and box Q1 moves one grid right.
    "spare": "9160ca72868cff6481d8b64854319a058955dc5b107271beb1c24219a1c581fd",
}


@pytest.mark.parametrize("name", ["canary", "spare"])
def test_the_drawn_text_and_rules_of_a_design_are_byte_identical(name, request) -> None:
    svgs = pages(request.getfixturevalue(name).model, tints=REF_TINTS)
    text = "\n".join(e for key in sorted(svgs) for e in _ELEMENT.findall(svgs[key]))
    assert hashlib.sha256(text.encode()).hexdigest() == PINS[name]


def test_contact_rows_are_the_oracle_rows_in_print_order_with_their_partners(canary, spare) -> None:
    """CR1: the NO column, then the NC column; a spare names no partner, any other its label's."""
    for built in (canary, spare):
        model = built.model
        for label in _tables(model):
            rows = contact_rows(model, label)
            assert [(r.text, (r.x, r.y, r.width, r.height)) for r in rows] == _rows(model, label)
            no, nc = contact_image(model, label)
            assert [r.text for r in rows] == [*no, *nc]
            assert [r.column for r in rows] == ["NO"] * len(no) + ["NC"] * len(nc)
            ports = {partner.port for partner in label.partners}
            assert all((r.partner is None) == r.text.endswith("N/A") for r in rows)
            assert {r.partner for r in rows if r.partner} <= ports
