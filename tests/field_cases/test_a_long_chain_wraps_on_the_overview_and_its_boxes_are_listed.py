"""Field case: one function block of 18 chained two-port devices on the overview's All devices view.

Engineering shape: a unit holds two function blocks. The first has a terminal strip and 18 fuses in
one series chain between two of its terminals; the second holds a lamp that the chain's return
terminal feeds. The reader opens the block and switches to "All devices".

The bugs (legacy finding C1): the 18 devices stood in one row 1880 G wide, so the page fitted the
row to the canvas and printed every label about 4 px high, and a canvas label is no text that the
DOM, Ctrl-F or a screen reader finds. The panel said "22 boxes, 21 lines" and named none of them.

Fix: overview-0008. A row wider than the view wraps into more rows, in chain order, each cut
between two columns; the page data holds `order` per view, its boxes in reading order, and the
panel lists them by designation, a click selecting the box. The browser itself is not in the gate
(overview-0001): the tests read the page's data and its script text.
"""

import json
import re
from typing import Any, NamedTuple

import fransys as fr
import pytest
from _model_build_cover import system_document
from fransys.colours import RD
from fransys_overview._js_panels import JS_PANELS

_CHAIN = 18
_SHAPE = (1050, 920)  # `PACK_SHAPE`: the canvas the page fits at true size, in G


class _Io(NamedTuple):
    pass


@fr.unit("demo-rs", revision=1, interface_version=1, date="2026-10-14", text="first", by="AB")
def _rs(u: fr.Design) -> _Io:
    with u.function("B1", "Block"):
        strip = u.terminal_strip("X1", "DEMO-TB-2.5")
        feed, back = strip.run("A", 1), strip.run("B", 1)
        fuses = [u.device(f"G{n}", "DEMO-FUSE-DC-160") for n in range(1, _CHAIN + 1)]
    with u.function("B2", "Other"):
        lamp = u.device("H1", "DEMO-LAMP-24")
    u.series(*[f.element for f in fuses], wire=(RD, 1.0))
    u.wire(feed[1], fuses[0].element["1"], wire=(RD, 1.0))
    u.wire(fuses[-1].element["2"], back[1], wire=(RD, 1.0))
    u.wire(back[1], lamp["1"], wire=(RD, 1.0))
    return _Io()


@pytest.fixture(scope="module")
def data(tmp_path_factory) -> dict[str, Any]:
    d = fr.design("demo_parts")
    d.project(title="FC", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-14", text="First issue", created="XX")
    d.add(_rs, "U1")
    written = fr.write(fr.build(d, system_document()), tmp_path_factory.mktemp("out"))
    page = next(p for p in written if p.name.endswith("overview.html")).read_text()
    block = re.search(r'id="overview-data">(.*?)</script>', page, re.DOTALL)
    assert block is not None
    return json.loads(block.group(1))


@pytest.fixture(scope="module")
def block_view(data) -> dict[str, Any]:
    """The All devices view of the first block, opened (`level` a group, no strip open)."""
    found = [
        v
        for v in data["views"]
        if v["mode"] == "see_through" and v["level"] is not None and v["open"] is None
    ]
    return max(found, key=lambda v: len(v["boxes"]))


def _chain(view: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        (b for b in view["boxes"] if re.fullmatch(r"-G\d+", b["lines"][0])),
        key=lambda b: int(b["lines"][0][2:]),
    )


def _rows(boxes: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Boxes in row bands: a box starts a new band when it begins below the band's least bottom."""
    rows: list[list[dict[str, Any]]] = []
    for box in sorted(boxes, key=lambda b: (b["y"], b["x"])):
        if rows and box["y"] < min(b["y"] + b["h"] for b in rows[-1]):
            rows[-1].append(box)
        else:
            rows.append([box])
    return rows


def test_the_view_holds_the_whole_chain(block_view) -> None:
    """Passes on base: the repro is the view the legacy report names, not a smaller one."""
    assert [b["lines"][0] for b in _chain(block_view)] == [f"-G{n}" for n in range(1, _CHAIN + 1)]


def test_no_box_passes_the_view_width(block_view) -> None:
    """Breaks if the chain stays one row wider than the canvas (the fit shrinks every label)."""
    assert max(b["x"] + b["w"] for b in block_view["boxes"]) <= _SHAPE[0]


def test_the_view_fits_the_canvas_so_labels_keep_their_size(block_view) -> None:
    """The page fits at true size at most, so a view inside the canvas prints labels at 1:1."""
    assert max(b["x"] + b["w"] for b in block_view["boxes"]) <= _SHAPE[0]
    assert max(b["y"] + b["h"] for b in block_view["boxes"]) <= _SHAPE[1]


def test_the_chain_wraps_into_more_than_one_row(block_view) -> None:
    """Breaks if the chain stays in one band."""
    assert len(_rows(_chain(block_view))) > 1


def test_the_rows_keep_the_chain_order(block_view) -> None:
    """Breaks if a wrap shuffles the devices: rows read top down, each row left to right."""
    rows = _rows(_chain(block_view))
    assert len(rows) > 1
    names = [b["lines"][0] for row in rows for b in sorted(row, key=lambda b: b["x"])]
    assert names == [f"-G{n}" for n in range(1, _CHAIN + 1)]


def test_a_box_is_as_big_as_in_a_short_chain(block_view) -> None:
    """Passes on base: a wrap moves boxes and never scales one (no label gets smaller)."""
    assert {b["h"] for b in _chain(block_view)} <= {48, 72}
    assert {b["w"] for b in _chain(block_view)} <= {32, 40}


def test_the_data_lists_every_box_in_reading_order(block_view) -> None:
    """Breaks if the panel has no list: every box once, the chain's devices in chain order."""
    order = block_view["order"]
    assert sorted(order) == list(range(len(block_view["boxes"])))
    names = [block_view["boxes"][i]["lines"][0] for i in order]
    assert [n for n in names if re.fullmatch(r"-G\d+", n)] == [
        f"-G{n}" for n in range(1, _CHAIN + 1)
    ]


def test_the_panel_lists_the_boxes_and_a_click_selects_one() -> None:
    """Breaks if the list is not drawn as DOM text, or its entry does not select its box."""
    assert "view.order.map" in JS_PANELS
    assert "state.sel = 'b' + i" in JS_PANELS


def test_the_panel_list_reads_as_the_drawing_wrapped_row_then_x_then_y(block_view) -> None:
    """Breaks if the strip drawn under -G2 is listed after -G10 instead of after -G2."""
    names = [block_view["boxes"][i]["lines"][0] for i in block_view["order"]]
    assert names == [
        "-G1", "-G2", "-X1", "-G3", "-G4", "-G5", "-G6", "-G7", "-G8", "-G9", "-G10",
        "-G11", "-G12", "-G13", "-G14", "-G15", "-G16", "-G17", "-G18", "=B2",
    ]  # fmt: skip
