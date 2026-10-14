"""The words of a page hint that names a group with no column (layout-0195).

Private to `stages.partition`. A group loses its column when a current loop runs through its
devices and other groups' devices: the loop's chain column holds them all and has no one group.
The message names the group that took the devices, the loop, and the `d.layout.chain` fix.
"""

from typing import TYPE_CHECKING

from .lookups import group_of

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .types import Column, FunctionSpec, GroupInfo, Handle

BASE = "a page hint names a group with no column"


def refusal_message(
    group: Handle,
    columns: Sequence[Column],
    specs: Sequence[FunctionSpec],
    infos: Mapping[Handle, GroupInfo],
) -> str:
    """The base text, then, for each column that holds the group's devices, its loop and the fix."""
    by_function = {spec.function: spec for spec in specs}
    held = [
        [by_function[cell.function] for cell in column.cells if cell.function in by_function]
        for column in columns
    ]
    parts = [
        _sentence(group, cells, infos) for cells in held if any(group_of(s) == group for s in cells)
    ]
    return " ".join([f"{BASE}: {_name(group, infos)} has none.", *parts]) if parts else BASE


def _name(group: Handle, infos: Mapping[Handle, GroupInfo]) -> str:
    """A group by designation, with its description when it has one."""
    info = infos.get(group)
    if info is None:
        return "a group"
    return (
        f"group {info.designation} ({info.description})"
        if info.description
        else (f"group {info.designation}")
    )


def _sentence(
    group: Handle, cells: Sequence[FunctionSpec], infos: Mapping[Handle, GroupInfo]
) -> str:
    """One column: the group that took the devices, the loop, and the chain that keeps them home."""
    others = list(dict.fromkeys(g for s in cells if (g := group_of(s)) not in (group, None)))
    loop = " - ".join(spec.designation for spec in cells)
    taken = ", ".join(_name(other, infos) for other in others) or "another column"
    text = f"Its devices stand in the column of {taken}, pulled there by the loop {loop}."
    own = [spec for spec in cells if group_of(spec) == group]
    if len(own) > 1:
        chain = ", ".join(f"<function of {spec.designation}>" for spec in own)
        text += f" d.layout.chain({chain}) keeps them in the column of {_name(group, infos)}."
    return text
