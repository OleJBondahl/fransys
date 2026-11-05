"""A copied hub is one device on two pages: the drawn netlist joins them (el-0071, R552)."""

from types import SimpleNamespace
from typing import Any

import pytest
from fransys_el import drawn_where
from fransys_el.drawn_graph import Union
from fransys_el.drawn_netlist import _join_copies

from fransys_model.kernel import Id, make_id
from fransys_model.layout import LinkMarker, MarkerPair, MarkerSide, Page, Side, StarKind
from fransys_model.vocab import Port

P1, P2 = Id[Page](kind="page", value="p1"), Id[Page](kind="page", value="p2")
HUB, COPY = Id[Port](kind="port", value="hub"), Id[Port](kind="port", value="copy")


def _stub(page: Id[Page], port: Id[Port], far: Id[Port]) -> LinkMarker:
    ident = make_id(LinkMarker, ("t", str(page), str(port)))
    return LinkMarker(
        id=ident, key=("t", str(page), str(port)), page=page, port=port, side=MarkerSide.OWNER,
        partner=ident, x=0, y=0, width=1, height=1, produced_by="t", star=StarKind.OFF, pairs=(MarkerPair(port=port, far=far),),
        facing=Side.N,
    )  # fmt: skip


def _joined(*stubs: tuple[LinkMarker, tuple[Id[Page], tuple[int, int]] | None]) -> bool:
    union = Union()
    hub, copy = (P1, (0, 0)), (P2, (5, 5))
    _join_copies(union, {r.id.value: node for r, node in stubs}, {r.id.value: r for r, _ in stubs})
    return union.find(hub) == union.find(copy)


def test_a_copy_joins_its_hubs_page_to_its_own():
    hub, copy = (_stub(P1, HUB, COPY), (P1, (0, 0))), (_stub(P2, COPY, HUB), (P2, (5, 5)))
    assert _joined(hub, copy)
    assert not _joined(copy)


def test_a_stub_that_stands_on_no_node_joins_nothing():
    hub, copy = (_stub(P1, HUB, COPY), (P1, (0, 0))), (_stub(P2, COPY, HUB), None)
    assert not _joined(hub, copy)


def test_a_stub_whose_far_port_is_on_its_own_page_joins_nothing():
    hub, copy = (_stub(P2, HUB, COPY), (P2, (0, 0))), (_stub(P2, COPY, HUB), (P2, (5, 5)))
    union = Union()
    _join_copies(union, {r.id.value: node for r, node in (hub, copy)}, {r.id.value: r for r, _ in (hub, copy)})
    assert union.find((P2, (0, 0))) != union.find((P2, (5, 5)))


def _where_net(text: str) -> tuple[Any, Any]:
    """The placements of terminal `s` (P1 cell 1A, P2 cell 2B) and a net double whose P1 drawing prints `text` as its where-text."""
    places = {"f": [(P1, SimpleNamespace(column=1, row="A")), (P2, SimpleNamespace(column=2, row="B"))]}
    drawing = SimpleNamespace(texts=[SimpleNamespace(owner="sym", text=text)])
    other = SimpleNamespace(texts=[SimpleNamespace(owner="sym", text="p1:1A")])
    net = SimpleNamespace(owners={"s": "sym"}, ids={"s": "s"}, pages={P1: SimpleNamespace(drawing=drawing), P2: SimpleNamespace(drawing=other)})
    return places, net


@pytest.mark.rule("DRAWN-NETLIST")
def test_a_where_text_joins_only_when_it_is_the_other_placements_position(monkeypatch: pytest.MonkeyPatch) -> None:
    """R1397: the text is compared with the recomputed position; a cell off by one joins nothing."""
    places, net = _where_net("p2:2B")
    monkeypatch.setattr(drawn_where, "function_placements", lambda _model: places)
    monkeypatch.setattr(drawn_where, "port_function", lambda _model, _port: "f")
    monkeypatch.setattr(drawn_where, "where_text", lambda _m, _here, there: f"p{there[0].value[1]}:{there[1].column}{there[1].row}")
    assert drawn_where.where_joined(None, net) == {"s"}  # ty: ignore[invalid-argument-type] - doubles
    net.pages[P1].drawing.texts[0].text = "p2:2C"
    assert drawn_where.where_joined(None, net) == set()  # ty: ignore[invalid-argument-type] - doubles
