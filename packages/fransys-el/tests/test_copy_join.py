"""A copied hub is one device on two pages: its where-text joins them (el-0071, R552)."""

from types import SimpleNamespace
from typing import Any

import pytest
from fransys_el import drawn_where

from fransys_model.kernel import Id
from fransys_model.layout import Page

P1, P2 = Id[Page](kind="page", value="p1"), Id[Page](kind="page", value="p2")


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
