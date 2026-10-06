"""Decision model-0118: a `mount`, `busbar` or `rail` conductor closes its net and is no wire."""

import pytest
from derive_helpers import add_all

from fransys_model.derive import wire_rows
from fransys_model.derive.closure import net_of
from fransys_model.kernel import Draft, Id, Origin, freeze
from fransys_model.vocab import WireFacet
from fransys_model.vocab.connectivity import Conductor
from fransys_model.vocab.core import Function, Item, Port
from fransys_model.vocab.enums import ConductorKind, FunctionKind, PortRole
from fransys_model.vocab.tables import facets_of


def _end(name: str) -> tuple[Item, Function, Port]:
    value = name * 32
    item = Item(
        id=Id(kind="item", value=value),
        key=(name,),
        part=None,
        parent=None,
        position=None,
        tag=f"-X{name}",
        description="terminal",
    )
    function = Function(
        id=Id(kind="function", value=value),
        key=(name, "terminal"),
        item=item.id,
        template=None,
        name="terminal",
        kind=FunctionKind.TERMINAL,
    )
    port = Port(
        id=Id(kind="port", value=value),
        key=(name, "terminal", "1"),
        function=function.id,
        template=None,
        name="1",
        role=PortRole.GENERIC,
    )
    return item, function, port


@pytest.mark.parametrize("kind", ["MOUNT", "RAIL", "BUSBAR"])
def test_a_link_conductor_closes_its_net_and_carries_no_wire_facet(
    kind: str, origin: Origin
) -> None:
    """Can-fail: giving the conductor a `WireFacet` fails the facet and the wire-label asserts."""
    (item_a, fn_a, port_a), (item_b, fn_b, port_b) = _end("a"), _end("b")
    conductor = Conductor(
        id=Id(kind="conductor", value="1" * 32),
        key=("link",),
        a=port_a.id,
        b=port_b.id,
        kind=ConductorKind[kind],
        carrier=None,
    )
    draft = Draft()
    add_all(draft, item_a, item_b, fn_a, fn_b, port_a, port_b, conductor, origin=origin)
    model = freeze(draft)
    assert net_of(model, port_a.id) == net_of(model, port_b.id)
    assert not facets_of(model, WireFacet)
    assert wire_rows(model) == ()
