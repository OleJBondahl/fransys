"""Field case: a cable between two board instances names each far end with its instance tag.

The engineering shape: two identical I/O boards, tagged `U1` and `U2`, at one place, joined by
a cable between their connectors.

The bug: a stub's far end was cut out of the port text by string slicing, so it read the unit's
own root tag (`-U9-J1`) for both boards and named neither instance.

The rule (UT2): the one rendering in `fransys_model.derive` gives the far end its instance
tag, head `-U1-J1` and tail `:1`; `stub_far_end` calls it and no longer slices strings.

The decision that fixes it: model-0134.
"""

from functools import cache
from typing import Any, NamedTuple

import fransys as fr

from fransys_model.derive.drawing_text import stub_far_end
from fransys_model.vocab.tables import functions, ports


class _Io(NamedTuple):
    J1: fr.Device


@cache
def _board() -> Any:
    @fr.unit(
        "demo-board", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB"
    )
    def board(u: Any) -> _Io:
        root = u.device("U9", "DEMO-PCB-IO")
        return _Io(u.device("J1", "DEMO-CONN-2P", parent=root, interface=True))

    return board


def _port(model: fr.Model, device: fr.Device, name: str) -> Any:
    return next(
        i
        for i, p in ports(model).items()
        if functions(model)[p.function].item == device.id and p.name == name
    )


def test_each_far_end_carries_its_instance_tag() -> None:
    d = fr.design("demo_parts", place="C1")
    d.location("C1", "Cabinet")
    a = d.add(_board(), "U1")
    b = d.add(_board(), "U2")
    cable = d.cable("W1", "DEMO-CBL-4G1.5")
    cable.core(1, a.J1["1"], b.J1["1"])
    model = fr.build(d).model
    head_a, tail_a = stub_far_end(model, _port(model, a.J1, "1"))
    head_b, tail_b = stub_far_end(model, _port(model, b.J1, "1"))
    assert head_a.endswith("-U1-J1")
    assert head_b.endswith("-U2-J1")
    assert (tail_a, tail_b) == (":1", ":1")
