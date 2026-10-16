"""EL-2 earth and protection lane: the derive site `open_core_ends` pinned before and after.

`open_ends_at` picks the ports of a terminal by `PortRole`; the lane switches that read to
`port_role`. The output must not move (model-0292).
"""

from plant import Plant
from query_builders import make_strip
from test_cable_open_core_texts import _plant

from fransys_model.derive.open_core_ends import open_ends_at
from fransys_model.kernel import make_id
from fransys_model.vocab.core import Item
from fransys_model.vocab.enums import PortRole
from fransys_model.vocab.tables import ports


def test_open_ends_at_lists_the_core_on_the_terminal_port_of_its_role() -> None:
    # MUTATION: `open_ends_at` matches the ports of any role
    plant = Plant()
    _, (_, _, n1) = make_strip(plant)
    plant, _ = _plant(plant=plant, open_at=n1.external)
    model = plant.model()
    terminal = make_id(Item, ("x1", "t-n1"))
    role = ports(model)[n1.external].role
    assert open_ends_at(model, terminal, role, unit=None) == ("-W1 WH spare",)
    other = next(r for r in PortRole if r is not role)
    assert open_ends_at(model, terminal, other, unit=None) == ()
