"""EF-D part 2: undo tests for D7's "a lane that carries an image reserves the image's width".

K1 and K2 are two 2CO relays whose coils are wired in parallel (D1: K2's coil is K1's side
element, in K1's row one lane over), each with contacts elsewhere, so each has a contact image.
The items carry no group, so their tags are short and the lane pitch is narrower than an image.
An image is a `CROSS_REFERENCE` label with slot "contacts", read as `test_dd_contact_images.py`
reads it; its box is rebuilt from its text with the measurement the engine draws it with.
"""

from functools import cache
from typing import TYPE_CHECKING

import fransys as fr
import fransys_author
import fransys_parts
from _model_build_cover import layout_trigger_document
from test_dd_contact_images import _box, _cabinet, _images, _lane_x, _placement, _relays

from fransys_layout.engines.schematic.read.house import DEFAULT_PROFILE, DEFAULT_SHEET
from fransys_layout.geometry import WIRING_GRID, text_width
from fransys_layout.stages._image_widest import widest_where
from fransys_layout.stages.images import _image_width
from fransys_model.derive.drawing_text import label_text
from fransys_model.layout import Label, Page, layout_of

if TYPE_CHECKING:
    from fransys_model.kernel import Finding, Model


@cache
def _parallel_coils() -> tuple[Model, tuple[Finding, ...]]:
    """K1, K2: 2CO relays with coils on the same two nets; each one's contact feeds an output."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(
        title="EF-D",
        number="P-6",
        customer="Example Co",
        revision=1,
        author="OJB",
    )
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    c1 = d.location("C1", "Cabinet")
    strip = d.strip("X1", at=c1)
    feed, zero, out1, out2, out3 = (strip.terminal("DEMO-TB-2.5") for _ in range(5))
    k1 = d.item("DEMO-RLY-2CO-24", tag="K1", at=c1)
    k2 = d.item("DEMO-RLY-2CO-24", tag="K2", at=c1)
    wire = d.wiring(colour="BU", gauge="0.5")
    wire(feed.inner, k1.fn("coil")["A1"])
    wire(k1.fn("coil")["A1"], k2.fn("coil")["A1"])
    wire(k1.fn("coil")["A2"], zero.inner)
    wire(k1.fn("coil")["A2"], k2.fn("coil")["A2"])
    for relay, out in ((k1, out1), (k2, out2)):
        wire(feed.inner, relay.fn("co_1")["11"])
        wire(relay.fn("co_1")["14"], out.inner)
        wire(relay.fn("co_1")["12"], out3.inner)
    result = fr.build(parts, d.draft(), layout_trigger_document())
    return result.model, tuple(result.findings)


def test_the_two_coils_stand_in_one_row_and_each_image_under_its_own_lane() -> None:
    """D7: K2's coil is K1's side element (one row, two lanes); each image is at its coil's wire."""
    model, _ = _parallel_coils()
    k1, k2 = (_placement(model, tag, "coil") for tag in ("K1", "K2"))
    assert k1.page == k2.page
    assert k1.y == k2.y
    assert k1.x != k2.x
    images = _images(model)
    assert set(images) == {"K1", "K2"}
    offsets = {images[tag].x - _lane_x(coil) for tag, coil in (("K1", k1), ("K2", k2))}
    assert len(offsets) == 1


def test_the_next_lane_stands_clear_of_an_image_and_no_text_overlaps() -> None:
    """D7: an image ends left of the next lane's leftmost text; the images do not overlap."""
    # UNDO: stages/images.py `reserved`: drop the width from the grown keep-out
    # (no `beside` box: `grow_keepout(one.geometry, [below])` only).
    model, findings = _parallel_coils()
    k1, k2 = (_placement(model, tag, "coil") for tag in ("K1", "K2"))
    (tag,) = (
        label
        for label in layout_of(model, Label).values()
        if label.function == k2.function and label.slot == "tag"
    )
    left, right = sorted(_images(model).values(), key=lambda label: label.x)
    assert k1.x < k2.x
    assert _box(model, left)[2] <= right.x
    assert _box(model, left)[2] + WIRING_GRID <= tag.x  # the next lane's leftmost text
    assert [f for f in findings if "TEXT_OVERLAP" in str(f.code)] == []


def test_the_widest_place_text_covers_every_page_and_column() -> None:
    """D7, D13: whatever page a contact lands on, its place text is no wider than the reserve's."""
    # UNDO: stages/_image_widest.py `widest_where`: `range(1, 2)` for the pages.
    height = DEFAULT_PROFILE.text_height
    columns = DEFAULT_SHEET.frame_columns
    for pages in (1, 9, 10, 100):
        widest = widest_where(pages, DEFAULT_SHEET, DEFAULT_PROFILE)
        for page in (1, pages):
            for column in (1, columns):
                assert text_width(f"/{page}.{column}", height=height) <= text_width(
                    widest, height=height
                )


def test_a_drawn_image_is_never_wider_than_the_width_reserved_for_it() -> None:
    """D7, D13: the reserve measures the widest place text, so no drawn image outgrows it."""
    # UNDO: stages/images.py `image_width`: `return 2 * (column + 2 * profile
    # .marker_padding) - 8` (the reserve is then narrower than the image `_box` rebuilds).
    checked = 0
    for model in (_cabinet(), _relays(), _parallel_coils()[0]):
        pages = max(page.number for page in layout_of(model, Page).values())
        widest = widest_where(pages, DEFAULT_SHEET, DEFAULT_PROFILE)
        for image in _images(model).values():
            marks = [
                entry.split()[0]
                for line in label_text(model, image).split("\n")[1:]
                for entry in line.split(" | ")
                if entry.strip()
            ]
            x0, _, x1, _ = _box(model, image)
            assert x1 - x0 <= _image_width([f"{mark} {widest}" for mark in marks], DEFAULT_PROFILE)
            checked += 1
    assert checked >= 5
