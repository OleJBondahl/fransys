"""WP14: the synthetic cabinet freezes in every flag combination and holds what its spec lists."""

import itertools
from typing import TYPE_CHECKING, Any

import pytest
from layout_cabinet import build_cabinet

from fransys_model.kernel import freeze, make_id
from fransys_model.layout import Chain, GroupHint, layout_of
from fransys_model.vocab import (
    Item,
    LinkKind,
    aspect_nodes,
    conductors,
    function_templates,
    internal_links,
    items,
    nets,
    parts,
    port_templates,
)

if TYPE_CHECKING:
    from fransys_model.kernel import Model

FLAGS = ("reverse", "extra_relay", "broken_chain", "second_location")
COMBINATIONS = [
    dict(zip(FLAGS, values, strict=True)) for values in itertools.product((False, True), repeat=4)
]


def _model(**flags: bool) -> Model:
    return freeze(build_cabinet(**flags))


def _item(model: Model, *key: str) -> Item | None:
    return items(model).get(make_id(Item, ("cabinet", *key)))


@pytest.mark.parametrize(
    "flags", COMBINATIONS, ids=lambda flags: "+".join(k for k in flags if flags[k]) or "default"
)
def test_freezes_in_every_flag_combination(flags: dict[str, Any]) -> None:
    assert _model(**flags).digest


@pytest.mark.parametrize(
    "extra", [{}, {"extra_relay": True}, {"broken_chain": True, "second_location": True}]
)
def test_reverse_gives_an_equal_digest(extra: dict[str, Any]) -> None:
    assert _model(**extra).digest == _model(reverse=True, **extra).digest


def test_extra_relay_adds_k9() -> None:
    assert _item(_model(), "k9") is None
    assert _item(_model(extra_relay=True), "k9") is not None


def test_broken_chain_adds_one_chain() -> None:
    before = len(layout_of(_model(), Chain))
    assert len(layout_of(_model(broken_chain=True), Chain)) == before + 1


def test_second_location_adds_the_location_c2() -> None:
    def labels(model: Model) -> set[str]:
        return {node.label for node in aspect_nodes(model).values()}

    assert "C2" not in labels(_model())
    assert {"C1", "C2"} <= labels(_model(second_location=True))


def test_items_are_found_by_key() -> None:
    model = _model()
    assert _item(model, "w1") is not None
    k8 = _item(model, "k8")
    assert k8 is not None
    assert k8.installed is False
    board = _item(model, "a1")
    child = _item(model, "a1", "f1")
    assert board is not None
    assert child is not None
    assert child.parent == board.id


def test_one_group_hint_and_no_other_layout_kind_but_chains_and_symbol_choices() -> None:
    model = _model()
    assert len(layout_of(model, GroupHint)) == 1
    assert {kind for kind in model.tables if kind.startswith("layout.")} == {
        "layout.chain",
        "layout.group_hint",
        "layout.symbol_choice",
    }


def test_exactly_one_net_has_no_conductor_on_its_ports() -> None:
    model = _model()
    wired = {end for conductor in conductors(model).values() for end in (conductor.a, conductor.b)}
    bare = [net for net in nets(model).values() if not wired & set(net.ports)]
    assert len(bare) == 1
    assert len(bare[0].ports) == 2


def test_the_contactor_main_contact_has_three_disjoint_poles() -> None:
    model = _model()
    contactor = next(part for part in parts(model).values() if part.mpn == "EX-CONTACTOR-3P")
    templates = {t.name: t for t in function_templates(model).values() if t.part == contactor.id}
    assert set(templates) == {"coil", "main", "aux"}
    pins = port_templates(model)
    links = [
        frozenset((pins[link.a].name, pins[link.b].name))
        for link in internal_links(model).values()
        if pins[link.a].function == templates["main"].id
        and pins[link.b].function == templates["main"].id
        and link.kind is LinkKind.SWITCHED
    ]
    assert len(links) == 3
    assert len(frozenset().union(*links)) == 6
    assert set(links) == {frozenset("12"), frozenset("34"), frozenset("56")}
