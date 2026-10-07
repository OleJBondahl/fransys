"""Hand-built `BlockFacts` for the cable placer's tests (CT5-3): no model, only widths and ids.

`block_facts(cores)` takes one `(top end, bottom end)` pair per core, core keys 1, 2, ...; each
row runs its ends by lowest core key and each end its pins in core order, as `end_rows` and
`drawn_pins` give them. Nothing here names a real plant.
"""

from dataclasses import replace
lazy from collections.abc import Sequence

from fransys_layout.engines.cable.values import (
    BlockFacts,
    CableFacts,
    CoreFacts,
    EndFacts,
    PinFacts,
)
from fransys_model.kernel import make_id
from fransys_model.vocab import Conductor, Item, Port

TEXT_HEIGHT = 16


def _pin(name: str) -> PinFacts:
    return PinFacts(port=make_id(Port, (name,)), landed=True, marking_width=16)


def _row(
    side: str, ends: list[int], label: int, *, blank: bool = False
) -> tuple[tuple[EndFacts, ...], dict[tuple[int, int], str]]:
    """The row's ends by lowest core key, and each (end, core) pin's port name."""
    order = list(dict.fromkeys(ends))
    pins: dict[tuple[int, int], str] = {}
    built = []
    for end in order:
        ports = []
        for core, owner in enumerate(ends):
            if owner == end:
                pins[end, core] = f"{side}{end}.{core}"
                ports.append(_pin(pins[end, core]))
        built.append(
            EndFacts(
                item=make_id(Item, (f"{side}{end}",)),
                dashed=False,
                blank=blank,
                label_width=label,
                pins=tuple(ports),
            )
        )
    return tuple(built), pins


def block_facts(
    cores: list[tuple[int, int]],
    *,
    label: int = 48,
    text: int = 40,
    bottom_blank: bool = False,
    loops: Sequence[tuple[bool, int]] = (),
) -> BlockFacts:
    """The facts of one block whose core i runs from top end `cores[i][0]` to bottom end [1].

    Each `(on_top, end index)` of `loops` adds a link core after the crossing ones, on two new pins
    appended to that end (the index counts the row's ends by lowest core key).
    """
    top, top_pins = _row("t", [t for t, _ in cores], label)
    bottom, bottom_pins = _row("b", [b for _, b in cores], label, blank=bottom_blank)
    rows = {True: list(top), False: list(bottom)}
    links = []
    for n, (on_top, end) in enumerate(loops):
        names = [f"{'t' if on_top else 'b'}{end}.L{n}{c}" for c in "ab"]
        rows[on_top][end] = replace(
            rows[on_top][end], pins=(*rows[on_top][end].pins, *(_pin(name) for name in names))
        )
        k = len(cores) + n
        links.append(
            CoreFacts(
                key=k + 1,
                conductor=make_id(Conductor, (f"c{k}",)),
                end_a=make_id(Port, (names[0],)),
                end_b=make_id(Port, (names[1],)),
                text_width=text,
                link=True,
            )
        )
    top, bottom = tuple(rows[True]), tuple(rows[False])
    core_facts = tuple(
        CoreFacts(
            key=i + 1,
            conductor=make_id(Conductor, (f"c{i}",)),
            end_a=make_id(Port, (top_pins[t, i],)),
            end_b=make_id(Port, (bottom_pins[b, i],)),
            text_width=text,
        )
        for i, (t, b) in enumerate(cores)
    ) + tuple(links)
    return BlockFacts(
        subject=make_id(Item, ("w",)),
        unit=None,
        sheet_format=None,
        text_height=TEXT_HEIGHT,
        turn_penalty=4,
        crossing_penalty=16,
        pad=8,
        cables=(
            CableFacts(
                cable=make_id(Item, ("w",)), external=False, heading_width=64, cores=core_facts
            ),
        ),
        top=top,
        bottom=bottom,
    )
