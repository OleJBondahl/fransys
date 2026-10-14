"""An authored chain's box-drawn ends (layout-0181): the head or tail may stand in an item box."""

from typing import TYPE_CHECKING, NamedTuple

from fransys_layout.geometry import HintError

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from collections.abc import Set as AbstractSet

    from .types import Chain, ChainEntry, FunctionSpec, Handle, PortSpec

type Steps = list[tuple[ChainEntry, FunctionSpec]]


class Ends(NamedTuple):
    """The box-drawn functions a chain starts or ends at; each stays in its own box column."""

    head: FunctionSpec | None = None
    tail: FunctionSpec | None = None


def resolve(
    chain: Chain, specs: Mapping[Handle, FunctionSpec], boxes: Mapping[Handle, FunctionSpec]
) -> Steps:
    """Every entry with its spec: a box entry from `boxes`, any other from `specs`."""
    found: Steps = []
    for entry in chain.entries:
        spec = boxes.get(entry.function) if entry.box else specs.get(entry.function)
        if spec is None:
            msg = "a chain names a function that is not drawn"
            raise HintError(msg, subjects=(chain.chain, entry.function))
        found.append((entry, spec))
    return found


def split_ends(
    chain: Chain, steps: Sequence[tuple[ChainEntry, FunctionSpec]]
) -> tuple[Steps, Ends]:
    """The steps drawn in the chain's column, and the box-drawn head and tail beside them."""
    last = len(steps) - 1
    for at, (entry, spec) in enumerate(steps):
        if entry.box and 0 < at < last:
            msg = "a chain may name a box-drawn function only at its head or its tail"
            raise HintError(msg, subjects=(chain.chain, spec.function))
    head = steps[0][1] if steps[0][0].box else None
    tail = steps[last][1] if last > 0 and steps[last][0].box else None
    inner = [step for step in steps if not step[0].box]
    if not inner:
        msg = "a chain names only box-drawn functions"
        raise HintError(msg, subjects=(chain.chain,))
    return inner, Ends(head=head, tail=tail)


def box_entry(
    spec: FunctionSpec, ends: Ends, joined: AbstractSet[tuple[Handle, Handle]]
) -> list[PortSpec]:
    """The ports of the first step `spec` that face a box-drawn head, else leave a lone tail's."""
    if ends.head is not None:
        head = {port.port for port in ends.head.ports}
        return [p for p in spec.ports if any((p.port, n) in joined for n in head)]
    if ends.tail is None:
        return []
    tail = {port.port for port in ends.tail.ports}
    wired = {a for a, _ in joined}
    return [
        p for p in spec.ports if p.port in wired and all((p.port, n) not in joined for n in tail)
    ]
