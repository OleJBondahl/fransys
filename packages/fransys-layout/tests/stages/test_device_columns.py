"""LC2 (layout-0215): each device chain is one column, its devices one row each in chain order."""

from samples import function_spec, hid

from fransys_layout.stages.device_columns import device_columns
from fransys_layout.stages.types import DeviceChain


def test_each_chain_is_one_column_keyed_by_its_first_device_rows_in_chain_order() -> None:
    """Chain 3-1-2 is keyed by function 3's key and lists 3, 1, 2 at rows 0, 1, 2 in lane 0."""
    specs = [function_spec(n) for n in range(1, 6)]
    chains = (
        DeviceChain(members=(hid("function", 3), hid("function", 1), hid("function", 2)), hops=()),
        DeviceChain(members=(hid("function", 5), hid("function", 4)), hops=()),
    )
    first, second = device_columns(chains, specs)
    assert first.key == ("invented", "fn3")
    assert [(c.function, c.index, c.lane) for c in first.cells] == [
        (hid("function", 3), 0, 0),
        (hid("function", 1), 1, 0),
        (hid("function", 2), 2, 0),
    ]
    assert second.key == ("invented", "fn5")
    assert [(c.function, c.index, c.lane) for c in second.cells] == [
        (hid("function", 5), 0, 0),
        (hid("function", 4), 1, 0),
    ]
