"""A fault path through a motor or a coil is left out as a load's is (spec API-CLARITY C6.7, A9).

`actuator` and `coil` take energy by default (model-0232), so the fault graph treats them as
loads: the fuse behind one reads no source, while the same fuse behind a plain conductor reads
the module's 6000 A.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from current_plant import device, fuse, hub, run
from fault_plant import module
from plant import Plant
from rating_plant import rail, supply

from fransys_model.derive import prospective_fault
from fransys_model.vocab.enums import Current, FunctionKind, LinkKind

if TYPE_CHECKING:
    from fransys_model.kernel import Model


def _behind(kind: FunctionKind) -> Model:
    """A 6000 A module on a bus; plus bus, then a 20 A `kind` function `MOT`, then the fuse `G`."""
    plant = Plant()
    plus, minus = hub(plant, "P"), hub(plant, "M")
    plant.net("bus+", (plus,), potential="B+")
    plant.net("bus-", (minus,), potential="B-")
    supply(
        plant, "bat", {"B+": rail("48"), "B-": rail("0")}, current=Current.DC, pins=(plus, minus)
    )
    run(plant, minus, [module(plant, "m", "6000", "2")], plus)
    node = hub(plant, "N")
    motor = device(plant, "MOT", amps="20", link=LinkKind.CONDUCTIVE, kind=kind)
    run(plant, plus, [motor], node)
    run(plant, node, [fuse(plant, "G", "10")], minus)
    return plant.model()


def _fault_at_the_fuse(kind: FunctionKind) -> Decimal | None:
    (found,) = prospective_fault(_behind(kind))
    return found.current_a


@pytest.mark.parametrize("kind", [FunctionKind.ACTUATOR, FunctionKind.COIL, FunctionKind.LOAD])
def test_a_fault_path_through_a_motor_or_coil_is_left_out_like_a_load(kind: FunctionKind) -> None:
    assert _fault_at_the_fuse(kind) == Decimal(0)


def test_the_same_path_through_a_plain_conductor_carries_the_module_current() -> None:
    assert _fault_at_the_fuse(FunctionKind.GENERIC) == Decimal(6000)
