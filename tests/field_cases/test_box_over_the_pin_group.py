"""Field case: a box that feeds one pin group of another box stands over that group.

The engineering shape: two power supplies side by side, each with an AC input on top and a DC
output below, and a redundancy module with one input group per supply and an output to the 24 V
and 0 V rails. Each supply's output is wired plus to plus and minus to minus to its own group.

The bug: the module's groups do not stand under their feeders, so the supply wires bend or cross
on the way to the module, and a supply authored second can end up over the first one's group.
The rule (decision layout-0107): a box fed by one box over a whole pin
group is placed so pin stands under pin, and every wire between them is one vertical segment.
"""

import tempfile
from pathlib import Path

import fransys as fr
from _drawn_pages import drawn_pages
from fransys.colours import BU

from fransys_model.layout import PowerSymbol, layout_of
from fransys_model.vocab.tables import functions, items, ports


def _gap(model, fact: str):
    """A fact the page Drawing lacks (strict xfail, GAP-FLIP-DRAWING-SUBJECT)."""
    msg = f"GAP-FLIP-DRAWING-SUBJECT: no {fact} for {model.digest}"
    raise AssertionError(msg)


def _plant(d, order: tuple[str, str]) -> None:
    with d.function("G", "Group"):
        psus = {tag: d.device(tag, "DEMO-PSU-24") for tag in order}
        module = d.device("U1", "DEMO-RED-2IN")
    live = d.terminal_strip("X1", "DEMO-TB-2.5", 2).run("L", 2, bridged=True)
    zero = d.terminal_strip("X2", "DEMO-TB-2.5", 2).run("L", 2, bridged=True)
    d.dc_supply("S", plus=live[1], minus=zero[1], voltage=24)
    d.detail.wire(module.out["+"], live[1].outer, wire=(BU, 0.5))
    d.detail.wire(module.out["-"], zero[1].outer, wire=(BU, 0.5))
    for tag, group, n in (("T1", module.in_1, "1"), ("T2", module.in_2, "2")):
        d.detail.wire(psus[tag].output["+"], group[f"{n}+"], wire=(BU, 0.5))
        d.detail.wire(psus[tag].output["-"], group[f"{n}-"], wire=(BU, 0.5))


def _built(order: tuple[str, str]):
    """The model of the two supplies and the module, authored in `order`."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    _plant(d, order)
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    return fr.build(d, doc).model


def _box(model, tag: str):
    """The generic box drawn for the item tagged `tag`; its owner text starts with the tag."""
    found = [
        one
        for one in _gap(model, "symbol subject")
        if one.key == "generic-box" and one.owner and one.owner.split()[0] == tag
    ]
    assert len(found) == 1, f"{tag} is drawn as {len(found)} boxes"
    return found[0]


def _pin_x(box, name: str) -> int:
    return box.x + dict(box.offsets)[name]


def _overlap(a, b) -> bool:
    """Two boxes of one page whose pin spans meet in x and stand at one y (the body is symdef's)."""

    def span(box):
        offsets = dict(box.offsets).values()
        return box.x + min(offsets), box.x + max(offsets)

    (ax0, ax1), (bx0, bx1) = span(a), span(b)
    return a.page == b.page and a.y == b.y and ax0 <= bx1 and bx0 <= ax1


def _check(order: tuple[str, str]) -> None:
    model = _built(order)
    module = _box(model, "U1")
    pairs = (("T1", "in_1", "1"), ("T2", "in_2", "2"))
    outs_x = set()
    for tag, group, number in pairs:
        psu = _box(model, tag)
        for out, pin in (("+", "+"), ("-", "-")):
            outs_x.add(_pin_x(psu, f"output.{out}"))
            assert _pin_x(psu, f"output.{out}") == _pin_x(module, f"{group}.{number}{pin}")
    wires = [
        w
        for page, drawing in drawn_pages(model).items()
        if page == module.page
        for w in drawing.wires
        if any(p[0] in outs_x for p in (w.points[0], w.points[-1]))
    ]
    assert len(wires) == 4
    assert all(len({p[0] for p in w.points}) == 1 for w in wires), "a wire bends"
    boxes = [_box(model, tag) for tag in ("T1", "T2", "U1")]
    for i, a in enumerate(boxes):
        for b in boxes[i + 1 :]:
            assert not _overlap(a, b), "two boxes overlap"
    (module_item,) = (one.id for one in items(model).values() if one.tag == "U1")
    outs = {
        pid
        for pid, p in ports(model).items()
        if functions(model)[p.function].item == module_item
        and functions(model)[p.function].key[-1] == "out"
    }
    drawn = {s.port for s in layout_of(model, PowerSymbol).values()}
    assert len(outs) == 2
    assert outs <= drawn, "the module's output pins draw power symbols"


def test_each_supply_stands_over_its_own_pin_group_of_the_redundancy_module() -> None:
    """Output pins share x with the group's pins, no wire bends, no box overlaps, power symbols."""
    _check(("T1", "T2"))


def test_the_pairing_sets_the_x_when_the_supplies_are_authored_in_swapped_order() -> None:
    """The second supply authored first still stands over its own group."""
    _check(("T2", "T1"))
