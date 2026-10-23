"""Tests: `item_box_views` groups an item's functions into one generic box (layout-0123)."""

from typing import Any

from plant import Plant

from fransys_model.derive import BoxCandidate, item_box_views
from fransys_model.derive.item_boxes import box_port_text


class _Item:
    """An invented item of three functions `a`, `b`, `c` with ports `10`, `2`, `1`."""

    def __init__(self) -> None:
        plant = Plant()
        self.item = plant.item("k1")
        self.functions = {n: plant.function(self.item, n) for n in "abc"}
        self.ports = {
            n: plant.port(f, p)
            for (n, f), p in zip(self.functions.items(), ("10", "2", "1"), strict=True)
        }
        self.model = plant.model()

    def candidate(self, name: str, **flags: Any) -> BoxCandidate:
        """The candidate of function `name`: boxed by default."""
        values: dict[str, Any] = {
            "function": self.functions[name],
            "item": self.item,
            "key": ("k1", name),
            "band": "relay",
            "plc_channel": False,
            "pin": False,
            "boxed": True,
            "ports": (self.ports[name],),
            "symbol": "",
            "symbol_ports": (),
        }
        return BoxCandidate(**{**values, **flags})


def test_two_boxed_functions_form_one_box_with_ranked_port_names() -> None:
    """Functions rank by first marking (`c`, `b`, `a`); names are `<function>.<port>`."""
    one = _Item()
    wired = frozenset(one.ports.values())
    (view,) = item_box_views(one.model, [one.candidate(n) for n in "abc"], wired)
    assert view.members == tuple(one.functions.values())
    assert view.lead == one.functions["a"]
    assert (view.kind, view.named, view.lone) == ("relay", False, False)
    assert {(b.name, b.rank) for b in view.ports} == {("a.10", 2), ("b.2", 1), ("c.1", 0)}


def test_the_unboxed_function_stands_apart() -> None:
    """With two boxed functions the third draws on its own."""
    one = _Item()
    candidates = [one.candidate("a"), one.candidate("b"), one.candidate("c", boxed=False)]
    (view,) = item_box_views(one.model, candidates, frozenset())
    assert view.members == (one.functions["a"], one.functions["b"])
    assert view.apart == (one.functions["c"],)
    assert view.kind == "item"


def test_one_boxed_function_leaves_the_item_alone() -> None:
    """A box needs two; one boxed function and one drawn by its symbol give no row."""
    one = _Item()
    candidates = [one.candidate("a"), one.candidate("b", boxed=False)]
    assert item_box_views(one.model, candidates, frozenset()) == ()


def test_the_kind_is_shared_by_the_wired_members_only() -> None:
    """Two kinds on wires give "item"; a single wired kind wins over an unwired other."""
    one = _Item()
    a, b = one.candidate("a"), one.candidate("b", band="coil")
    both = frozenset(one.ports.values())
    (view,) = item_box_views(one.model, [a, b], both)
    assert view.kind == "item"
    (view,) = item_box_views(one.model, [a, b], frozenset({one.ports["b"]}))
    assert view.kind == "coil"


def test_functions_naming_one_symbol_with_distinct_ports_are_a_named_box() -> None:
    """Authored choices all naming one symbol draw the item by it, unless a port repeats."""
    one = _Item()
    named = [
        one.candidate(n, boxed=False, symbol="s", symbol_ports=(p,))
        for n, p in (("a", "1"), ("b", "2"))
    ]
    (view,) = item_box_views(one.model, named, frozenset())
    assert view.named
    clash = [one.candidate(n, boxed=False, symbol="s", symbol_ports=("1",)) for n in "ab"]
    assert item_box_views(one.model, clash, frozenset()) == ()
    pinned = [
        *named[:1],
        one.candidate("b", boxed=False, symbol="s", symbol_ports=("2",), pin=True),
    ]
    assert item_box_views(one.model, pinned, frozenset()) == ()


def test_a_lone_unwired_plc_channel_is_its_own_item_box() -> None:
    """Wired, it stays a channel of its module's box (no row for one function)."""
    one = _Item()
    channel = one.candidate("a", plc_channel=True)
    (view,) = item_box_views(one.model, [channel], frozenset())
    assert (view.lone, view.kind, view.members, view.ports) == (
        True,
        "item",
        (channel.function,),
        (),
    )
    assert item_box_views(one.model, [channel], frozenset(channel.ports)) == ()


def test_the_text_of_a_box_port() -> None:
    """The name is the function's, a dot, the port's."""
    assert box_port_text("fn", "13") == "fn.13"
