"""Field case: a pin wired to a non-rail terminal shows that terminal at the pin (V4, 2026-10-02).

The engineering shape: a feed-through terminal X1:1 whose outer side is wired to a switch and
whose inner side feeds the coil pin A1 of one, two or more relays. Four layouts of it: the relays
on a page after the terminal's (one relay; two relays in one group; two relays in two groups
sharing the page) and the relays in the terminal's own group (a star of three ports).

The bug (v0.5.2 look): the terminal stood once per page, as the home or one replica. A second
pin on the page was a branch of a star marker naming the terminal as the reference, and a replica
serving two pins stood at neither. The one-relay layout already drew the replica over the pin.

The rule (decision layout-0108): every pin wired to a non-rail terminal shows
the terminal at the pin, in every group and for any wire count; terminal references go.
Model-0220 changed the count: the terminal stands at each relay's pin, not once over the first.
"""

import tempfile
from pathlib import Path
from typing import Any

import fransys as fr
import pytest
from _drawn_facts import symbol_subjects
from _drawn_pages import drawn_pages
from fransys.colours import BU

from fransys_model.vocab.tables import functions, items


def _feed(d: fr.Design, groups: list[str], *, coils: list[int], pin: str = "A1") -> dict[int, Any]:
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
                d.detail.wire(switch.sw["B"], terminal.outer, wire=(BU, 0.5))
            for k, at in enumerate(coils, start=1):
                if at == number:
                    relay = d.device(f"K{k}", "DEMO-RLY-2CO-24")
                    d.detail.wire(terminal, relay.coil[pin], wire=(BU, 0.5))
    return opened


def _one_relay(d: fr.Design, g: list[str]) -> None:
    d.layout.break_before(_feed(d, g, coils=[1])[1])


def _one_relay_fed_at_a2(d: fr.Design, g: list[str]) -> None:
    """The same relay fed at its other coil pin: the layout stands the coil unturned."""
    d.layout.break_before(_feed(d, g, coils=[1], pin="A2")[1])


def _two_relays_one_group(d: fr.Design, g: list[str]) -> None:
    d.layout.break_before(_feed(d, g, coils=[1, 1])[1])


def _two_relays_two_groups(d: fr.Design, g: list[str]) -> None:
    d.layout.break_before(_feed(d, g, coils=[1, 2])[1])


def _own_group(d: fr.Design, g: list[str]) -> None:
    _feed(d, g, coils=[0, 0])


def _built(plant) -> Any:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    plant(d, [f"G{i}" for i in range(3)])
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    return fr.build(d, doc).model


def _symbols(model, key: str) -> list[tuple[object, Any]]:
    """The (page, drawn symbol) pairs of library symbol `key`, on every page."""
    return [
        (page, s)
        for page, drawing in drawn_pages(model).items()
        for s in drawing.symbols
        if s.key == key
    ]


def _drawn(model, name: str, tag: str = "") -> list[tuple[object, Any]]:
    """The (page, drawn symbol) pairs of function `name` of item `tag`, or of every terminal."""
    item_tag = {i.id: i.tag for i in items(model).values()}
    owned = {
        f.id.value
        for f in functions(model).values()
        if f.key[-1] == name and (not tag or item_tag.get(f.item, "") == tag)
    }
    return [(s.page, s) for s in symbol_subjects(model) if s.owner in owned]


def _assert_terminal_over_pin(terminals, page, coil) -> None:
    """One terminal on the relays' page, over the coil's pin; the other relays keep a wire."""
    on_page = [t for p, t in terminals if p == page]
    assert len(on_page) == 1, f"{len(on_page)} terminals on the relays' page, one is the rule"
    assert on_page[0].x == coil.x
    assert on_page[0].y < coil.y, "the terminal is not over the coil's pin"
    assert len({p for p, _ in terminals}) == len(terminals)


def _assert_drawn_at_each_relays_pin(model, relays: int) -> None:
    """Model-0220: one terminal per relay on the page, each over its own relay's coil pin."""
    terminals = _symbols(model, "terminal")
    coils = _symbols(model, "operating-device")
    assert len(coils) == relays, f"{len(coils)} relay coils drawn, {relays} relays"
    for page, coil in coils:
        over = [t for p, t in terminals if p == page and t.x == coil.x and t.y < coil.y]
        assert len(over) == 1, f"{len(over)} terminals over a relay's pin, one is the rule"


def _assert_replica_beyond_pin(drawing, terminals, coil) -> None:
    """One terminal in the coil's column, outside the body, on the edge its pin lead leaves by."""
    (terminal,) = [t for t in terminals if t.x == coil.x]
    body, box = coil.outline, terminal.outline
    ends = [pt for w in drawing.wires for pt in (w.points[0], w.points[-1])]
    below, above = box.y >= body.y + body.h, box.y + box.h <= body.y
    assert below or above, "the terminal stands inside the coil's body"
    pin_edge = body.y + body.h if below else body.y
    near_edge = box.y if below else box.y + box.h
    assert (coil.x, pin_edge) in ends, "no lead leaves the coil body on the terminal's side"
    assert (coil.x, near_edge) in ends, "the lead does not reach the terminal"


@pytest.mark.rule("PORT-LINE")
@pytest.mark.parametrize(
    ("plant", "orient"),
    [(_one_relay, "R180"), (_one_relay_fed_at_a2, "R0")],
    ids=["turned", "unturned"],
)
def test_one_relay_on_a_later_page_has_the_terminal_replica_over_its_pin(plant, orient) -> None:
    """PORT-LINE (R467 Q33): the replica stands beyond the pin, outside the body, turned or not.

    Fed at A1 the coil stands turned (R180, pin below); fed at A2 it stands unturned (R0).
    """
    model = _built(plant)
    ((page, coil),) = _symbols(model, "operating-device")
    assert coil.orient == orient
    on_page = [t for p, t in _symbols(model, "terminal") if p == page]
    drawing = next(d for p, d in drawn_pages(model).items() if p == page)
    _assert_replica_beyond_pin(drawing, on_page, coil)


def test_two_relays_of_one_group_have_the_terminal_at_each_relays_pin() -> None:
    model = _built(_two_relays_one_group)
    _assert_drawn_at_each_relays_pin(model, 2)


def test_two_relays_of_two_groups_on_one_page_have_the_terminal_at_each_relays_pin() -> None:
    model = _built(_two_relays_two_groups)
    _assert_drawn_at_each_relays_pin(model, 2)


def test_two_relays_in_the_terminals_own_group_have_the_terminal_over_the_first_pin() -> None:
    model = _built(_own_group)
    ((page, coil),) = (p for p in _drawn(model, "coil", "K1") if p[1].key == "operating-device")
    _assert_terminal_over_pin(_drawn(model, "terminal"), page, coil)
