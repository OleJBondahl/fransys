"""D5 step 6: the power symbols and their texts do not follow the order of the stage inputs.

The shuffle of `test_layout_is_independent_of_the_order_of_the_stage_inputs`, over the invented
plant of `power_fixture` (eleven power ends, four pages): the layout, with its symbols and
labels, and the written power records are the same whatever order the input tuples come in.
"""

from dataclasses import replace
from typing import TYPE_CHECKING

import pytest
from power_fixture import power_run

from fransys_layout.engines.schematic import run_stages
from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read.write_keys import write_keys
from fransys_layout.engines.schematic.write import write_layout
from fransys_layout.stages.texts.power import power_places
from fransys_model.layout import POWER_SLOT, PowerSymbol, layout_of

if TYPE_CHECKING:
    from collections.abc import Callable

    from fransys_layout.engines.schematic.read import StageInputs


def _reordered(inputs: StageInputs, order: Callable[[tuple], tuple]) -> StageInputs:
    """`inputs` with every tuple of records in another order: what a different iteration gives."""
    return replace(
        inputs,
        functions=order(inputs.functions),
        connections=order(inputs.connections),
        net_groups=order(inputs.net_groups),
        rails=order(inputs.rails),
        chains=order(inputs.chains),
        choices=order(inputs.choices),
        groups=order(inputs.groups),
        locations=order(inputs.locations),
        label_texts=order(inputs.label_texts),
    )


_ORDERS = [lambda records: records[::-1], lambda records: records[1::2] + records[::2]]


@pytest.mark.parametrize("order", _ORDERS, ids=["reversed", "interleaved"])
def test_power_layout_is_independent_of_the_order_of_the_stage_inputs(
    order: Callable[[tuple], tuple],
) -> None:
    """UNDO: in `power_places` or `with_power_labels` sort by `id(one)`: the order leaks in.

    The comparison is not vacuous: the layout holds power ends with labels, and the shuffle
    does change the tuples it permutes.
    """
    model, inputs, results, _ = power_run()
    shuffled = _reordered(inputs, order)
    assert shuffled != inputs
    layout, _, _ = run_stages(model, shuffled)
    assert layout == results.layout
    assert power_places(layout.markers)
    assert [one for one in layout.labels if one.slot == POWER_SLOT]


@pytest.mark.parametrize("order", _ORDERS, ids=["reversed", "interleaved"])
def test_the_written_power_symbols_do_not_follow_the_input_order(
    order: Callable[[tuple], tuple],
) -> None:
    """UNDO: in `power_symbols` key a record by its position in `power_places`."""
    model, inputs, results, _ = power_run()
    other, _ = stage_results(model, _reordered(inputs, order))
    keys = write_keys(model)
    once = layout_of(write_layout(model, results, keys), PowerSymbol)
    twice = layout_of(write_layout(model, other, keys), PowerSymbol)
    assert once == twice
    assert len(once) == 11
