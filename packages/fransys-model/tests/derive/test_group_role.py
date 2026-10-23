"""`group_role`: the class mapping, the strongest rule, PE not voting, an empty group (model-0318).

The old-engine equality lives in `internal/tests/test_group_role_equiv.py`.
"""

from typing import Any

import pytest
from plant import Plant

from fransys_model.derive import group_role
from fransys_model.kernel import make_id
from fransys_model.layout import PageRole
from fransys_model.vocab import AspectNode, Item, Net, Placement
from fransys_model.vocab.enums import Aspect, NetClass

GROUP = make_id(AspectNode, ("=G",))
OTHER = make_id(AspectNode, ("=H",))


def _model(*classes: NetClass | tuple[NetClass, ...] | None) -> Any:
    """Group `=G` holds item K1, one port per entry of `classes`: a net class,
    several (a net each on the one port) or `None` (un-netted)."""
    plant = Plant()
    for label, node in (("=G", GROUP), ("=H", OTHER)):
        plant.add(
            AspectNode(
                id=node,
                key=(label,),
                aspect=Aspect.FUNCTION,
                parent=None,
                label=label,
                description="",
            )
        )
    for index, entry in enumerate(classes):
        port = plant.pin("K1", "F", f"p{index}")
        for number, net_class in enumerate(entry if isinstance(entry, tuple) else (entry,)):
            if net_class is None:
                continue
            key = (f"n{index}", str(number))
            plant.add(
                Net(
                    id=make_id(Net, key),
                    key=key,
                    name=None,
                    net_class=net_class,
                    ports=(port,),
                    potential=None,
                )
            )

    plant.add(
        Placement(
            id=make_id(Placement, ("K1",)), key=("K1",), item=make_id(Item, ("K1",)), node=GROUP
        )
    )
    return plant.model()


@pytest.mark.parametrize(
    ("net_class", "role"),
    [
        (NetClass.POWER, PageRole.POWER),
        (NetClass.CONTROL, PageRole.CONTROL),
        (NetClass.GENERIC, PageRole.CONTROL),
        (NetClass.SIGNAL, PageRole.SIGNAL),
    ],
)
def test_a_net_class_maps_to_its_role(net_class: NetClass, role: PageRole) -> None:
    assert group_role(_model(net_class), GROUP) is role


@pytest.mark.parametrize(
    ("classes", "role"),
    [
        ((NetClass.SIGNAL, NetClass.CONTROL, NetClass.POWER), PageRole.POWER),
        ((NetClass.SIGNAL, NetClass.GENERIC), PageRole.CONTROL),
        ((NetClass.SIGNAL, NetClass.SIGNAL), PageRole.SIGNAL),
    ],
)
def test_the_strongest_net_decides(classes: tuple[NetClass, ...], role: PageRole) -> None:
    assert group_role(_model(*classes), GROUP) is role


def test_pe_does_not_vote_and_an_unnetted_port_votes_control() -> None:
    assert group_role(_model(NetClass.PE), GROUP) is PageRole.CONTROL
    assert group_role(_model(NetClass.SIGNAL, None), GROUP) is PageRole.CONTROL
    assert group_role(_model(NetClass.SIGNAL, NetClass.PE), GROUP) is PageRole.CONTROL
    assert group_role(_model((NetClass.SIGNAL, NetClass.PE)), GROUP) is PageRole.SIGNAL


def test_a_group_without_ports_is_control() -> None:
    assert group_role(_model(NetClass.POWER), OTHER) is PageRole.CONTROL
