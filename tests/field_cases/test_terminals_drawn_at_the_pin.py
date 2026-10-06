"""Field case: a pin wired to a non-rail terminal shows that terminal at the pin (V4, 2026-10-02).

The engineering shape: a feed-through terminal X1:1 whose outer side is wired to a switch and
whose inner side feeds the coil pin A1 of one, two or more relays. Four layouts of it: the relays
on a page after the terminal's (one relay; two relays in one group; two relays in two groups
sharing the page) and the relays in the terminal's own group (a star of three ports).

The bug (v0.5.2 look): the terminal stood once per page, as the home or one replica. A second
pin on the page was a branch of a star marker naming the terminal as the reference, and a replica
serving two pins stood at neither. The one-relay layout already drew the replica over the pin.

The rule (CONVENTIONS-V06 V4, decision layout-0099): every pin wired to a non-rail terminal shows
the terminal at the pin, in every group and for any wire count; terminal references go.
"""

import tempfile
from pathlib import Path
from typing import Any

import fransys as fr
from fransys.colours import BU

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_model.vocab.tables import functions, items


def _feed(d: fr.Design, groups: list[str], *, coils: list[int]) -> dict[int, Any]:
    """Terminal X1:1 in group 0 fed by switch S1; relay K<n> in `groups[coils[n]]`.

    Each group is one `function` block, opened in the order its first device is made.
    """
    strip = d.terminal_strip("X1", "DEMO-TB-2.5")
    opened: dict[int, Any] = {}
    terminal: Any = None
    for number in sorted({0, *coils}):
        with d.function(groups[number], f"Group {number}") as opened[number]:
            if number == 0:
                switch = d.device("S1", "DEMO-SWITCH-2P")
                terminal = strip[1]
                d.wire(switch.sw["B"], terminal.outer, wire=(BU, 0.5))
            for k, at in enumerate(coils, start=1):
                if at == number:
                    relay = d.device(f"K{k}", "DEMO-RLY-2CO-24")
                    d.wire(terminal, relay.coil["A1"], wire=(BU, 0.5))
    return opened


def _one_relay(d: fr.Design, g: list[str]) -> None:
    d.layout.break_before(_feed(d, g, coils=[1])[1])


def _two_relays_one_group(d: fr.Design, g: list[str]) -> None:
    d.layout.break_before(_feed(d, g, coils=[1, 1])[1])


def _two_relays_two_groups(d: fr.Design, g: list[str]) -> None:
    d.layout.break_before(_feed(d, g, coils=[1, 2])[1])


def _own_group(d: fr.Design, g: list[str]) -> None:
    _feed(d, g, coils=[0, 0])


def _built(plant) -> tuple:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    plant(d, [f"G{i}" for i in range(3)])
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    model = fr.build(d, doc).model
    results, _ = stage_results(model, read_inputs(model))
    return model, results.layout


def _placed_of(model, layout, tag: str, name: str) -> list:
    """The placements of function `name` of item `tag`, or of the terminal when `tag` is ''."""
    item_tag = {i.id: i.tag for i in items(model).values()}
    return [
        p
        for f in functions(model).values()
        for p in layout.placed
        if p.function == f.id
        and f.key[-1] == name
        and (item_tag.get(f.item, "") == tag or (not tag and f.key[-1] == "terminal"))
    ]


def _assert_drawn_once_over_the_first_pin(model, layout) -> None:
    """One terminal on the relays' page, over K1's pin; the other relays keep a wire."""
    terminals = _placed_of(model, layout, "", "terminal")
    (coil,) = _placed_of(model, layout, "K1", "coil")
    on_page = [t for t in terminals if (t.drawing_set, t.page) == (coil.drawing_set, coil.page)]
    assert len(on_page) == 1, f"{len(on_page)} terminals on the relays' page, one is the rule"
    assert on_page[0].at.x == coil.at.x
    assert on_page[0].at.y < coil.at.y, "the terminal is not over K1's pin"
    assert len({(t.drawing_set, t.page) for t in terminals}) == len(terminals)


def test_one_relay_on_a_later_page_has_the_terminal_replica_over_its_pin() -> None:
    """Passes today: the one-wire replica is attached to its host (R7 B8); no reference."""
    model, layout = _built(_one_relay)
    _assert_drawn_once_over_the_first_pin(model, layout)


def test_two_relays_of_one_group_have_the_terminal_once_over_the_first_pin() -> None:
    model, layout = _built(_two_relays_one_group)
    _assert_drawn_once_over_the_first_pin(model, layout)


def test_two_relays_of_two_groups_on_one_page_have_the_terminal_once_over_the_first_pin() -> None:
    model, layout = _built(_two_relays_two_groups)
    _assert_drawn_once_over_the_first_pin(model, layout)


def test_two_relays_in_the_terminals_own_group_have_the_terminal_over_the_first_pin() -> None:
    model, layout = _built(_own_group)
    _assert_drawn_once_over_the_first_pin(model, layout)
