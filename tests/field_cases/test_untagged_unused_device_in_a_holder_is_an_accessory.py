"""Field case ACCESSORY-UNUSED: one part is a tagged boundary terminal and an untagged accessory.
The bug: each footprinted accessory became an item of its own, with a designation, a netlist line and a drawn function.
Fixed by model-0333 (author-0066, designer ruling 25), an untagged parent= device with unused=True is an accessory."""

from itertools import pairwise
from typing import Any, NamedTuple

import fransys as fr
from _model_build_cover import unit_document
from fransys.colours import BU
from fransys_el import lay_out_core
from fransys_el.drawn_netlist import is_marker

from fransys_model import derive
from fransys_model.vocab.tables import items

_REL: dict[str, Any] = {"revision": 1, "interface_version": 1, "date": "2026-01-01"}
_FUSE = "DEMO-FUSE-HOLDER-PCB"


class _Io(NamedTuple):
    F1: Any


def _unit(*, unused: bool) -> Any:
    @fr.unit("demo-accessory", text="x", by="AB", **_REL)
    def unit(u: Any) -> _Io:
        board = u.device("A1", "DEMO-PCB-IO")
        f1 = u.device("F1", _FUSE, parent=board, interface=True)
        holder = u.device("H2", "DEMO-LAMP-24", parent=board)
        u.series(f1["1"], holder.lamp["1"], wire=(BU, 0.5))
        u.series(f1["2"], holder.lamp["2"], wire=(BU, 0.5))
        u.device(None, _FUSE, name="link-a", parent=holder, unused=unused)
        u.device(None, _FUSE, name="link-b", parent=holder, unused=unused)
        return _Io(F1=f1)

    return unit


def _build(tmp_path: Any, *, unused: bool) -> Any:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    u1 = d.add(_unit(unused=unused), "U1")
    h9 = d.device("H9", "DEMO-LAMP-24")  # outside the unit: the unit is not standalone
    d.series(h9["1"], u1.F1["1"], wire=(BU, 0.5))
    d.series(h9["2"], u1.F1["2"], wire=(BU, 0.5))
    (tmp_path / "c.md").write_text("# c\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=tmp_path / "c.md")
    return fr.build(d, doc, unit_document("demo-accessory"))


def _links(model: Any) -> list[Any]:
    return [i for i in items(model).values() if i.key[-1] in {"link-a", "link-b"}]


def test_two_untagged_unused_devices_in_a_holder_are_accessories(tmp_path: Any) -> None:
    result = _build(tmp_path, unused=True)
    model = result.model
    links = _links(model)
    assert len(links) == 2
    holder = next(i for i in items(model).values() if i.tag == "H2")
    for link in links:
        assert derive.takes_parents_designation(model, link.id)
        assert derive.item_designation(model, link.id) == derive.item_designation(model, holder.id)
    rows = derive.designation_list(model)
    assert not {link.id for link in links} & {row.item for row in rows}
    board = next(i for i in items(model).values() if i.tag == "A1")
    netlist = derive.board_netlist(model, board.id)
    assert sorted(part.mpn for part in netlist.parts) == sorted([_FUSE, "DEMO-LAMP-24"])  # F1 and the holder H2, no link
    (line,) = [b for b in derive.bom_lines(model) if b.mpn == _FUSE]
    assert line.count == 3
    assert "UNCONNECTED_PIN" not in [f.code for f in fr.check(result)]


def test_a_footprinted_untagged_parent_device_without_unused_stays_an_item(tmp_path: Any) -> None:
    model = _build(tmp_path, unused=False).model
    for link in _links(model):
        assert not derive.takes_parents_designation(model, link.id)


def test_no_wire_runs_across_the_box_of_a_reference_marker(tmp_path: Any, monkeypatch: Any) -> None:
    """KI-632 MARKER-OBSTACLE (R1661): the F1:2-H2:2 leg crosses the +CAB-H9:2 marker box; a marker is a wire keep (owner 2026-10-29)."""
    caught: list[Any] = []
    original = lay_out_core.drawn_netlist
    monkeypatch.setattr(lay_out_core, "drawn_netlist", lambda *a: caught.append(original(*a)) or caught[-1])
    _build(tmp_path, unused=False)
    inside = [
        (m.key, w.points)
        for net in caught
        for part in net.pages.values()
        for m in part.drawing.symbols
        if m.outline is not None and is_marker(m)
        for w in part.drawing.wires
        for a, b in pairwise(w.points)
        if min(a[0], b[0]) < m.outline.x + m.outline.w
        and max(a[0], b[0]) > m.outline.x
        and min(a[1], b[1]) < m.outline.y + m.outline.h
        and max(a[1], b[1]) > m.outline.y
    ]
    assert inside == []
