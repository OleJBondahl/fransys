"""Field case ACCESSORY-UNUSED: one part is a tagged boundary terminal and an untagged accessory.

The engineering shape: a unit holds a board. One fuse-holder part is used once as a tagged,
footprinted interface field of the unit, and twice as an untagged accessory plugged into a lamp
holder on the board, its pins left open on purpose (`unused=True`). The author wants one part id
and one BOM line of count 3.

The bug: the footprint bar of `takes_parents_designation` made each footprinted accessory an
item of its own: a designation, a row, a netlist line, and its function drawn.
The rule (designer ruling 25, author-0066, model-0333): an untagged device with `parent=` and
`unused=True` is an accessory whatever its part holds. It prints its holder's designation, has no
designation row and no netlist line, draws nothing; the BOM counts every installed use on one line.
A footprinted untagged `parent=` device without `unused=` stays an ordinary item.
"""

from typing import Any, NamedTuple

import fransys as fr
from fransys.colours import BU

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
        u.detail.wire(f1["1"], holder.lamp["1"], wire=(BU, 0.5))
        u.detail.wire(f1["2"], holder.lamp["2"], wire=(BU, 0.5))
        u.device(None, _FUSE, name="link-a", parent=holder, unused=unused)
        u.device(None, _FUSE, name="link-b", parent=holder, unused=unused)
        return _Io(F1=f1)

    return unit


def _build(tmp_path: Any, *, unused: bool) -> Any:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    u1 = d.add(_unit(unused=unused), "U1")
    h9 = d.device("H9", "DEMO-LAMP-24")  # outside the unit: the unit is not standalone
    d.detail.wire(h9["1"], u1.F1["1"], wire=(BU, 0.5))
    d.detail.wire(h9["2"], u1.F1["2"], wire=(BU, 0.5))
    (tmp_path / "c.md").write_text("# c\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=tmp_path / "c.md")
    return fr.build(d, doc)


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
    assert [part.mpn for part in netlist.parts] == [_FUSE]  # F1 only
    (line,) = [b for b in derive.bom_lines(model) if b.mpn == _FUSE]
    assert line.count == 3
    assert "UNCONNECTED_PIN" not in [f.code for f in fr.check(result)]


def test_a_footprinted_untagged_parent_device_without_unused_stays_an_item(tmp_path: Any) -> None:
    model = _build(tmp_path, unused=False).model
    for link in _links(model):
        assert not derive.takes_parents_designation(model, link.id)
