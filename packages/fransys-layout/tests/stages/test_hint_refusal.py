"""layout-0195: the words of a page hint that names a group with no column."""

import dataclasses

from samples import column, function_spec, hid

from fransys_layout.stages import FunctionSpec, GroupInfo
from fransys_layout.stages._hint_refusal import BASE, refusal_message

_INFOS = {
    hid("aspect_node", 1): GroupInfo(
        group=hid("aspect_node", 1), key=("a",), label="A", description="Strip", designation="=A"
    ),
    hid("aspect_node", 2): GroupInfo(
        group=hid("aspect_node", 2), key=("b",), label="B", description="", designation="=B"
    ),
}
_A = hid("aspect_node", 1)


def _spec(number: int, group: int, **changes: object) -> FunctionSpec:
    return dataclasses.replace(
        function_spec(number, group=group), designation=f"=D{number}", **changes
    )


def test_a_group_in_no_column_keeps_the_base_text() -> None:
    other = _spec(1, 2)
    assert refusal_message(_A, [column("c", (1,), group=None)], [other], _INFOS) == BASE


def test_a_lone_device_of_the_group_names_the_loop_but_no_chain() -> None:
    specs = [_spec(1, 1), _spec(2, 2)]
    message = refusal_message(_A, [column("c", (1, 2), group=None)], specs, _INFOS)
    assert "column of group =B, pulled there by the loop =D1 - =D2." in message
    assert "d.layout.chain" not in message


def test_two_devices_of_the_group_name_the_chain_that_keeps_them() -> None:
    specs = [_spec(1, 1), _spec(2, 1)]
    message = refusal_message(_A, [column("c", (1, 2), group=None)], specs, _INFOS)
    assert "another column" in message
    assert "d.layout.chain(<function of =D1>, <function of =D2>) keeps them" in message
