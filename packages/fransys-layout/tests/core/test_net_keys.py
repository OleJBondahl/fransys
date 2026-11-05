"""ROUTING (layout-0394): the one home of a wire's net, a port end's key and the lone cut end."""

from __future__ import annotations

from fransys_layout.core.cut_ledger import _leads
from fransys_layout.core.flow_values import FlowGraph
from fransys_layout.core.net_keys import is_lone_cut, net_of_key, port_key
from fransys_layout.core.values import CutEnd, PinRef

from .flow_builders import free, net, problem

A, B = PinRef("A", "p"), PinRef("B", "p")


def test_a_bundle_trunk_wire_belongs_to_its_member_net() -> None:
    assert net_of_key("f:n1") == "n1"
    assert net_of_key("n1") == "n1"


def test_a_wired_pin_is_keyed_by_its_net_and_a_pin_of_no_net_by_a_sentinel() -> None:
    assert port_key({A: "n1"}, A) == "n1"
    assert port_key({A: "n1"}, B) == "pin:B.p"


def test_a_lone_cut_end_is_a_cut_net_of_one_pin() -> None:
    assert is_lone_cut(is_cut=True, pin_count=1)
    assert not is_lone_cut(is_cut=False, pin_count=1)
    assert not is_lone_cut(is_cut=True, pin_count=2)


def test_only_a_lone_cut_end_is_a_lead() -> None:
    """A cut pin on a two-pin net is neither while its mate stands on its page."""
    prob = problem(
        [free("A"), free("B")],
        [
            net("lone", "A.n", cut=(CutEnd(PinRef("A", "n"), "L"),)),
            net("two", "A.e", "B.e"),
            net("cut2", "A.s", "B.s", cut=(CutEnd(PinRef("A", "s")),)),
        ],
    )
    assert list(_leads(prob, FlowGraph((), (), (), (), ()), {"A": 1, "B": 1})) == [PinRef("A", "n")]
