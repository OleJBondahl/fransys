"""`derive.current_chains` groups rated current paths and bounds each position.

Every device is an item `key` with one function `f` (builders in `current_plant`). A chain is
read back as a set of positions, each a name (the item keys of its functions, "plug+sock" for a
mate) with its bounds, so neither the order of the positions nor the end a chain is read from
matters. The expected values are written by hand from the spec's law (a limit bounds a device
when every loop through it that holds a source passes the limit, the outside being one node that
holds a source), never copied from the output. A chain is a block: positions any two of which
lie on a common loop. A string ends at external items, so that the outside closes its loop; a
real dead end has no loop and no bound.
"""

import dataclasses
from typing import TYPE_CHECKING

import pytest
from current_plant import (
    changeover,
    device,
    external,
    fuse,
    run,
    wire,
)
from plant import Plant
from rating_plant import rail, supply

from fransys_model.derive import current_chains
from fransys_model.kernel import Id, make_id
from fransys_model.vocab import current_states
from fransys_model.vocab.core import Function, Item, Port
from fransys_model.vocab.current_graph import Wire
from fransys_model.vocab.enums import Current
from fransys_model.vocab.tables import functions

if TYPE_CHECKING:
    from fransys_model.kernel import Model

_Bound = tuple[str, str, str, str]
_Position = tuple[str, tuple[_Bound, ...]]
_Chain = frozenset[_Position]


def _name(model: Model, function: Id[Function], prefix: str = "") -> str:
    return functions(model)[function].key[0].removeprefix(prefix)


def _read(model: Model, prefix: str = "") -> set[_Chain]:
    """Every chain of `model` as a set of (position name, its bounds); `prefix` is dropped."""
    return {
        frozenset(
            (
                "+".join(sorted(_name(model, f, prefix) for f in position.functions)),
                tuple(
                    (b.kind.value, str(b.value), _name(model, b.by, prefix), b.role.value)
                    for b in position.bounds
                ),
            )
            for position in chain.positions
        )
        for chain in current_chains(model)
    }


_POLES = ("K1", "F1", "S", "F2", "K2")


# -- the outside -------------------------------------------------


# -- the law per consistent item state ------------


def _changeover_plant(*, with_e: bool = True) -> Plant:
    """`M` (100 A) on a changeover's make throw, `E` (120 A) on its break throw, the common
    through a 400 A fuse `F` to a 200 A `D`, all ends at external items. Without `with_e` the
    break throw is wired to nothing."""
    plant = Plant()
    common, make, brk = changeover(plant, "CO")
    for tag, throw, limit in (("M", make, "100"), ("E", brk, "120")):
        if tag == "M" or with_e:
            source = device(plant, tag, limit=limit)
            wire(plant, source[0], external(plant, f"T{tag}"))
            wire(plant, source[1], throw)
    run(plant, common, [fuse(plant, "F"), device(plant, "D", amps="200")], external(plant, "Td"))
    return plant


def test_closed_is_always_true_for_a_both_state_part_regardless_of_the_chosen_state() -> None:
    """The first clause `state == "both" or item is None` must short-circuit: an `and`, or a
    mutated `"both"` literal, would fall through to the assignment lookup and disagree with a
    chosen state that differs from the part's own."""
    item = make_id(Item, ("k",))
    part = Wire(Id(kind="port", value="p1"), Id(kind="port", value="p2"), item, "both")
    assert current_states._closed(part, {item: "rest"}, set()) is True


def _named_end(plant: Plant, key: str, tag: str, potential: str | None = None) -> Id[Port]:
    """An external item `key` printed as `tag`, its one port on `potential` when given."""
    plant.add(
        Item(
            id=make_id(Item, (key,)),
            key=(key,),
            part=None,
            parent=None,
            position=None,
            tag=tag,
            description="Invented",
            external=True,
        )
    )
    port = plant.port(plant.function(make_id(Item, (key,)), "f"), "p")
    if potential is not None:
        plant.net(f"net-{key}", (port,), potential=potential)
    return port


def _line(plant: Plant, left: Id[Port], right: Id[Port]) -> None:
    """`left - D1 - D2 - D3 - right`, three rated two-port devices in a line."""
    run(plant, left, [device(plant, name, amps="10") for name in ("D1", "D2", "D3")], right)


def _order(model: Model) -> list[str]:
    (chain,) = current_chains(model)
    return [_name(model, position.functions[0]) for position in chain.positions]


def _dc_supply(plant: Plant) -> None:
    rails = {"+24V": rail("24"), "0V": rail("0")}
    supply(plant, "S", rails, current=Current.DC)


def _tag(plant: Plant, key: str, tag: str) -> None:
    """Give the item `key` the designation `tag`."""
    at = next(i for i, record in enumerate(plant.records) if record.id == make_id(Item, (key,)))
    plant.records[at] = dataclasses.replace(plant.records[at], tag=tag)


@pytest.mark.parametrize("low_on_left", [True, False])
def test_a_chain_with_no_ranked_end_starts_at_the_lower_designation_text(
    *, low_on_left: bool
) -> None:
    """No end carries a ranked potential: the end device printed `-A1` comes before `-A2`."""
    plant = Plant()
    _line(plant, _named_end(plant, "TA", "-X1"), _named_end(plant, "TB", "-X2"))
    low, high = ("D1", "D3") if low_on_left else ("D3", "D1")
    _tag(plant, low, "-A1")
    _tag(plant, high, "-A2")
    assert _order(plant.model()) == [low, "D2", high]


def test_a_ranked_end_wins_over_a_lower_designation_text() -> None:
    """The end device printed `-A9` on `+24V` starts the chain before the unranked `-A1`."""
    plant = Plant()
    _dc_supply(plant)
    unranked = _named_end(plant, "TA", "-X1")
    ranked = _named_end(plant, "TB", "-X9", "+24V")
    _line(plant, unranked, ranked)
    _tag(plant, "D1", "-A1")
    _tag(plant, "D3", "-A9")
    assert _order(plant.model()) == ["D3", "D2", "D1"]
