"""V11, model-0121: `port_potential_rank` and `port_potential_current` read the supply's facts.

Built from `examples/demo-parts` only. The rank order is AC phases, DC above 0 V, the AC rail at
0 V, the DC rail at 0 V, DC below 0 V, then PE last; equal facts tie by potential text, since
declaration order is no model fact. A rail's name is never read.

Can-fail probes: `_order_key` returning one constant fails the order test; `_carried` reading
only the port's own nets fails the closure and changeover tests.
"""

from typing import Any

import fransys_parts
from fransys_author import Design

from fransys_model.derive import port_potential_current, port_potential_rank
from fransys_model.kernel import Id, Model, freeze, merge
from fransys_model.vocab import Current
from fransys_model.vocab import Port as ModelPort

_AC = {"L1": ("230", 0), "L2": ("230", 120), "N": ("0", None)}
_DC = {
    "M12": ("-12", None),
    "Z": ("0", None),
    "P12": ("12", None),
    "M24": ("-24", None),
    "P24": ("24", None),
}


def _design() -> Design:
    return Design(fransys_parts.load("demo_parts"))


def _freeze(d: Design) -> Model:
    return freeze(merge(fransys_parts.load("demo_parts"), d.draft()))


def _on_nets(d: Design, nets: dict[str, str]) -> dict[str, Any]:
    """One terminal per potential, its `inner` port on a declared net of that potential.

    `nets` maps a name to a potential; a potential `PE` is a net of class `pe`.
    """
    strip = d.strip("X1", at=d.location("C1", "Cabinet"))
    ends = {}
    for name, potential in nets.items():
        end = strip.terminal("DEMO-TB-2.5", name).inner
        d.net(name, end, cls="pe" if potential == "PE" else "power", potential=potential)
        ends[name] = end
    return ends


def _ranks(model: Model, ends: dict) -> dict[str, int | None]:
    return {name: port_potential_rank(model, end.id) for name, end in ends.items()}


def _by_rank(ranks: dict[str, int | None]) -> list[str]:
    """The names, lowest rank first; every one must have a rank."""
    assert None not in ranks.values()
    return sorted(ranks, key=lambda name: ranks[name] or 0)


def test_the_order_is_the_supply_facts_with_pe_last() -> None:
    d = _design()
    d.supply("MAINS", current="ac", rails=_AC)
    d.supply("CONTROL", current="dc", rails=_DC)
    ends = _on_nets(d, {name: name for name in (*_AC, *_DC)} | {"PE": "PE"})
    ranks = _ranks(_freeze(d), ends)
    order = _by_rank(ranks)
    assert order == ["L1", "L2", "P24", "P12", "N", "Z", "M12", "M24", "PE"]
    assert [ranks[name] for name in order] == list(range(9))


def test_a_name_never_decides_the_rank() -> None:
    """The same facts under other names rank the same way."""
    d = _design()
    d.supply("MAINS", current="ac", rails={"L": ("230", 0), "N": ("0", None)})
    d.supply("CONTROL", current="dc", rails={"GND": ("0", None), "12V": ("12", None)})
    ends = _on_nets(d, {name: name for name in ("L", "N", "GND", "12V")})
    ranks = _ranks(_freeze(d), ends)
    assert _by_rank(ranks) == ["L", "12V", "N", "GND"]


def test_equal_facts_tie_by_potential_text_whatever_the_declaration_order() -> None:
    """Models that differ only in rail declaration order are equal, so the tie cannot read it."""
    for declared in (("A", "B"), ("B", "A")):
        d = _design()
        d.supply("CONTROL", current="dc", rails=dict.fromkeys(declared, ("24", None)))
        ends = _on_nets(d, {name: name for name in ("A", "B")})
        assert _ranks(_freeze(d), ends) == {"A": 0, "B": 1}


def test_a_potential_no_supply_declares_has_no_rank_and_no_current() -> None:
    d = _design()
    d.supply("CONTROL", current="dc", rails={"24V": ("24", None)})
    ends = _on_nets(d, {"24V": "24V", "ZZ": "ZZ"})
    model = _freeze(d)
    assert port_potential_rank(model, ends["24V"].id) == 0
    assert port_potential_rank(model, ends["ZZ"].id) is None
    assert port_potential_current(model, ends["ZZ"].id) is None


def test_the_current_comes_from_the_supply_and_pe_has_none() -> None:
    d = _design()
    d.supply("MAINS", current="ac", rails=_AC)
    d.supply("CONTROL", current="dc", rails={"P24": ("24", None)})
    ends = _on_nets(d, {"L1": "L1", "N": "N", "P24": "P24", "PE": "PE"})
    model = _freeze(d)
    got = {name: port_potential_current(model, end.id) for name, end in ends.items()}
    assert got == {"L1": Current.AC, "N": Current.AC, "P24": Current.DC, "PE": None}


def _changeover(first: str, second: str) -> tuple[Model, dict]:
    """A relay contact `co_1` of a two-source plant: 12 on net `first`, 14 on net `second`."""
    d = _design()
    d.supply("SOURCE-A", current="ac", rails={"A1": ("230", 0)})
    d.supply("SOURCE-B", current="ac", rails={"B1": ("230", 120)})
    contact = d.item("DEMO-RLY-2CO-24", name="k1").fn("co_1")
    d.net("FIRST", contact["12"], cls="power", potential=first)
    d.net("SECOND", contact["14"], cls="power", potential=second)
    return _freeze(d), {"contact": contact}


def test_a_changeover_common_fed_from_two_sources_takes_the_lower_rank() -> None:
    for first, second in (("A1", "B1"), ("B1", "A1")):
        model, found = _changeover(first, second)
        contact = found["contact"]
        low, high = (
            port_potential_rank(model, contact["12"].id),
            port_potential_rank(model, contact["14"].id),
        )
        assert {low, high} == {0, 1}
        assert port_potential_rank(model, contact["11"].id) == 0  # the common reaches both


def test_a_port_not_in_the_model_has_no_rank() -> None:
    model = _freeze(_design())
    ghost: Id[ModelPort] = Id(kind="port", value="0" * 32)
    assert port_potential_rank(model, ghost) is None
    assert port_potential_current(model, ghost) is None


def test_a_pin_behind_a_fuse_ranks_as_the_rail_its_protective_link_crosses() -> None:
    """The rail closure crosses a PROTECTIVE link; a conductive one would only join the net."""
    d = _design()
    d.supply("CONTROL", current="dc", rails={"P24": ("24", None)})
    ends = _on_nets(d, {"P24": "P24"})
    fuse = d.item("DEMO-FUSE-ABAT", name="f1")
    wire = d.wiring(colour="BU", gauge="0.5")
    wire(ends["P24"], fuse["1"])
    behind = d.strip("X2", at=d.location("C2", "Cabinet")).terminal("DEMO-TB-2.5", "V").inner
    wire(fuse["2"], behind)
    model = _freeze(d)
    assert port_potential_rank(model, ends["P24"].id) == 0
    assert port_potential_rank(model, fuse["2"].id) == 0
    assert port_potential_rank(model, behind.id) == 0
