"""`joined_nets` and `port_clusters` (stages/references/nets): hand-made conductors.

`joined_nets` lists the ports of every net in first-seen order.

Conductor `n` from `samples.connection` runs from port `upper * 10 + 2` to port `lower * 10 + 1`.
"""

from typing import override
lazy from collections.abc import Iterator

from samples import connection, hid

from fransys_layout.stages.references.nets import _joined_nets
lazy from fransys_layout.stages import Connection


def _port(function: int, position: int):
    return hid("port", function * 10 + position)


def test_a_split_wire_ends_at_its_stand_in_and_the_terminal_port_counts_in_both_halves() -> None:
    # UNDO: stages/references/nets.py `joined_nets`:
    #   `nets[joined.find(stand_in)].append(port)` -> `pass`
    #   (the terminal's port is in one half only)
    into, out_of = connection(1, 1, 2), connection(2, 3, 2)  # both end at port 21
    terminal_port = _port(2, 1)

    _, nets = _joined_nets((into, out_of), {out_of.handle: terminal_port})

    assert nets == [[_port(1, 2), terminal_port], [_port(3, 2), terminal_port]]


def _stars(count: int) -> tuple[Connection, ...]:
    """`count` nets of three conductors each, meeting at the port of function `10 * net + 1`."""
    return tuple(
        connection(3 * net + leg, 10 * net + 1 + leg, 10 * net + 1)
        for net in range(count)
        for leg in (1, 2, 3)
    )


class _Counting(tuple):  # noqa: SLOT001 -- a tuple subclass counts its own passes, no slots needed
    passes = 0

    @override
    def __iter__(self) -> Iterator[Connection]:
        type(self).passes += 1
        return super().__iter__()
