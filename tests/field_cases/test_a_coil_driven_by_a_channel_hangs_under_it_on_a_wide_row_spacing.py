"""Field case: a coil driven by a PLC channel hangs under that channel, always (LEGACY-REVIEW R1).

The engineering shape: a controller box with six output channel pins in one group, each channel
driving a relay coil (A1); the relays stand in a second group, and each relay's contact switches
a lamp in a third group. The unit authors a wide row spacing (400), as a consumer's cabinet did.

The bug: far ends hung a coil under its channel only if the box's column still fitted the sheet
(layout-0074's fit gate). At a 400 row spacing the gate refused every coil, and it counted the
column's own coil cell twice, so each coil stood beside its contacts on another page with a
reference back to the module.

The rule (decision layout-0208, amended by R1): the fit gate never sends a channel's coil back;
a column too tall for its sheet continues as the next column (LC1, layout-0215).
"""

import tempfile
from functools import cache
from pathlib import Path
from typing import Any

import fransys as fr
from fransys.colours import BU

from fransys_model.layout import LinkMarker, layout_of
from fransys_model.vocab.tables import functions, items, ports


def _gap(model, fact: str):
    """A fact the page Drawing lacks (strict xfail, GAP-FLIP-DRAWING-SUBJECT)."""
    msg = f"GAP-FLIP-DRAWING-SUBJECT: no {fact} for {model.digest}"
    raise AssertionError(msg)


COUNT = 6
PINS = tuple(f"CH{j:02d}-" for j in range(1, COUNT + 1))


@cache
def _built() -> Any:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    d.layout.profile(hide_unused_pins=True, column_gap=4, row_spacing=400)
    with d.function("PLC", "Controller"):
        plc = d.device("A1", None, pins=PINS, external=True)
    with d.function("B", "Relays"):
        rail = d.terminal_strip("X2", "DEMO-TB-2.5", COUNT).run("R", COUNT, bridged=True)
        relays = [d.device(f"K{i + 1}", "DEMO-RLY-2CO-24") for i in range(COUNT)]
        for i, relay in enumerate(relays):
            d.detail.wire(plc[PINS[i]], relay.coil["A1"], wire=(BU, 0.5))
            d.detail.wire(relay.coil["A2"], rail[i + 1].outer, wire=(BU, 0.5))
    with d.function("L", "Loads"):
        live = d.terminal_strip("X3", "DEMO-TB-2.5", 1)
        for i, relay in enumerate(relays):
            lamp = d.device(f"P{i + 1}", "DEMO-LAMP-24")
            d.detail.wire(relay.co_1["14"], lamp.lamp["1"], wire=(BU, 0.5))
            d.detail.wire(lamp.lamp["2"], live[1].outer, wire=(BU, 0.5))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    return fr.build(d, doc).model


def _tagged(model) -> dict:
    """Each function's (item tag, function name)."""
    tag_of = {i.id: i.tag for i in items(model).values()}
    return {f.id: (tag_of[f.item], f.name) for f in functions(model).values()}


def _drawn(model) -> dict:
    """Each drawn symbol by its owner text `<tag> function:<id>`."""
    return {one.owner: one for one in _gap(model, "symbol subject").values()}


def test_every_coil_stands_under_its_channel_pin() -> None:
    model = _built()
    named = _tagged(model)
    drawn = _drawn(model)
    (box,) = (s for s in drawn.values() if s.key == "generic-box" and s.owner.startswith("A1 "))
    coil_of = {
        named[f][0]: drawn[f"{named[f][0]} function:{f.value}"]
        for f in named
        if named[f][1] == "coil"
    }
    for i, pin in enumerate(PINS, start=1):
        coil = coil_of[f"K{i}"]
        assert coil.page == box.page, i
        assert coil.x == box.x + dict(box.offsets)[pin], i  # the coil's `in` pin is at its origin x
        assert coil.y > box.y, i
    assert len({s.y for s in coil_of.values()}) == 1  # one row: the chained coil too


def test_no_marker_stands_at_a_channel_or_its_coil() -> None:
    """No coil has a reference back to the module: each channel wire is drawn as a wire.

    Coil A2 returns reach the rail on another page: their markers stay, and show the markers
    are read.
    """
    model = _built()
    by_id = ports(model)
    named = _tagged(model)
    markers = layout_of(model, LinkMarker).values()
    marked = {(*named[by_id[m.port].function], by_id[m.port].name) for m in markers}
    coils = {(f"K{i}", "coil") for i in range(1, COUNT + 1)}
    assert len({(tag, name) for tag, name, port in marked if port == "A2"} & coils) > 0
    assert not {m for m in marked if m[0] == "A1" or m[2] == "A1"}


def test_the_contacts_stay_with_the_loads_they_switch() -> None:
    model = _built()
    named = _tagged(model)
    pages: dict = {}
    for function, thing in ((f, named[f]) for f in named):
        for one in _drawn(model).values():
            if (one.owner or "").endswith(f"function:{function.value}"):
                pages.setdefault(thing, set()).add(one.page)
    for i in range(1, COUNT + 1):
        assert pages[(f"K{i}", "co_1")] == pages[(f"P{i}", "lamp")]
