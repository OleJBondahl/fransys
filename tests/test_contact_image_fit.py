"""Part 5B (layout-0087): every entry of a contact image fits inside its column, as drawn.

A changeover whose ports are named `COM`/`NC`/`NO`, or `1n1`/`1n2`/`1n4` (a pole prefix), prints
entries ("COM-NO 1A", the cell only on the coil's own page, model-0136) that a digit-only
estimate of the image cannot see: the box was then sized for the header alone and the NO text
ran across the divider. The test builds the design,
renders the page and measures the drawn `<text>` primitives against the drawn divider and box,
with `text_width` on each printed entry (the one measurement layout reserves the image with).
The parts are invented and written to a temporary library.
"""

import re
from decimal import Decimal
from pathlib import Path

import fransys as fr
import fransys_author
import fransys_parts
import pytest
from _model_build_cover import system_document
from fransys_render import pages
from fransys_render._numbers import grid_to_mm

from fransys_layout.geometry import text_width
from fransys_model.layout import Label, LabelKind, default_sheet_format, layout_of, profile_of

_TEXT = re.compile(r'<text class="label" x="([^"]+)" y="([^"]+)" font-size="[^"]+">([^<]*)</text>')
_LINE = re.compile(r'<line class="marker" x1="([^"]+)" y1="([^"]+)" x2="([^"]+)"')
_DEMO_TERMINAL = (
    Path(__file__).resolve().parent.parent
    / "examples"
    / "demo-parts"
    / "demo_parts"
    / "parts"
    / "terminal-feedthrough-2_5.toml"
)
_LIBRARY = 'schema = 1\nname = "fit-parts"\nversion = "0.1.0"\ndescription = "Invented."\n'
_RELAY = """schema = 1

[part]
mpn = "FIT-RLY-{mpn}"
manufacturer = "Demo"
description = "Relay, one changeover, 24 V DC coil"
category = "electromechanical"
class_code = "K"

[[function]]
name = "coil"
kind = "coil"
symbol = "operating-device"
ports = [
    {{ name = "A1", role = "generic", symbol_port = "in" }},
    {{ name = "A2", role = "generic", symbol_port = "out" }},
]

[[function]]
name = "co_1"
kind = "contact_co"
symbol = "change-over-contact"
ports = [
    {{ name = "{com}", role = "common" }},
    {{ name = "{brk}", role = "break" }},
    {{ name = "{make}", role = "make" }},
]
links = [
    {{ a = "{com}", b = "{brk}", kind = "switched" }},
    {{ a = "{com}", b = "{make}", kind = "switched" }},
]
"""


def _drawn_image(tmp_path: Path, names: tuple[str, str, str]) -> tuple[list, dict]:
    """Build a relay with ports `names` (common, break, make), render it: (texts, image geometry).

    Returns the `(x, baseline, string)` of every `<text>` inside the image's box, and a dict with
    the box's left, right and bottom and the divider's x, all in mm.
    """
    com, brk, make = names
    (tmp_path / "library.toml").write_text(_LIBRARY, encoding="utf-8")
    (tmp_path / "parts").mkdir()
    (tmp_path / "parts" / "terminal.toml").write_text(
        _DEMO_TERMINAL.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (tmp_path / "parts" / "relay.toml").write_text(
        _RELAY.format(mpn="CO", com=com, brk=brk, make=make), encoding="utf-8"
    )
    parts = fransys_parts.load_path(tmp_path)
    d = fransys_author.Design(parts)
    d.project(title="Fit", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-09-26", text="First issue", created="XX")
    c1, group = d.location("C1", "Cabinet"), d.group("CTL", "Control")
    strip = d.strip("X1", at=c1)
    feed, zero, out1, out2 = (strip.terminal("DEMO-TB-2.5", group=group) for _ in range(4))
    k1 = d.item("FIT-RLY-CO", tag="K1", at=c1, group=group)
    wire = d.wiring(colour="BU", gauge="0.5")
    wire(feed.inner, k1.fn("coil")["A1"])
    wire(k1.fn("coil")["A2"], zero.inner)
    wire(feed.inner, k1.fn("co_1")[com])
    wire(k1.fn("co_1")[make], out1.inner)
    wire(k1.fn("co_1")[brk], out2.inner)
    model = fr.build(parts, d.draft(), system_document()).model

    (label,) = (
        one
        for one in layout_of(model, Label).values()
        if one.kind is LabelKind.CROSS_REFERENCE and one.slot == "contacts"
    )
    sheet = default_sheet_format()
    (svg,) = pages(model).values()

    def mm_x(g: int) -> Decimal:
        return grid_to_mm(sheet.content_x_mm, g, sheet.module_mm)

    def mm_y(g: int) -> Decimal:
        return grid_to_mm(sheet.content_y_mm, g, sheet.module_mm)

    left, right = mm_x(label.x), mm_x(label.x + label.width)
    top, bottom = mm_y(label.y), mm_y(label.y + label.height)
    texts = [
        (Decimal(x), Decimal(y), string)
        for x, y, string in _TEXT.findall(svg)
        if left <= Decimal(x) < right and top < Decimal(y) <= bottom
    ]
    (divider,) = {
        Decimal(x1) for x1, y1, x2 in _LINE.findall(svg) if x1 == x2 and Decimal(y1) == top
    }
    return texts, {
        "left": left,
        "right": right,
        "bottom": bottom,
        "divider": divider,
        "module": sheet.module_mm,
        "text_height": profile_of(model).text_height,
    }


@pytest.mark.parametrize(
    ("names", "entry"),
    [
        pytest.param(("COM", "NC", "NO"), r"COM-NO \d+[A-Z]", id="com-nc-no"),
        pytest.param(("1n1", "1n2", "1n4"), r"1n1-1n4 \d+[A-Z]", id="pole-prefixed"),
    ],
)
def test_every_entry_of_a_changeover_image_ends_inside_its_column(
    tmp_path: Path, names: tuple[str, str, str], entry: str
) -> None:
    """The widest entry, header included, ends before the divider (NO) or the box (NC)."""
    texts, image = _drawn_image(tmp_path, names)
    strings = {string for *_, string in texts}
    assert {"NO", "NC"} <= strings
    assert any(re.fullmatch(entry, string) for string in strings), strings

    def right_edge(x: Decimal, string: str) -> Decimal:
        width = text_width(string, height=image["text_height"])
        return x + grid_to_mm(0, width, image["module"])

    no = [(x, string) for x, _, string in texts if x < image["divider"]]
    nc = [(x, string) for x, _, string in texts if x >= image["divider"]]
    assert len(no) >= 2
    assert len(nc) >= 2
    for x, string in no:
        assert right_edge(x, string) <= image["divider"], string
    for x, string in nc:
        assert right_edge(x, string) <= image["right"], string
    assert all(baseline <= image["bottom"] for _, baseline, _ in texts)
