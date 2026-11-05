"""Field case: a pin wired to a non-rail terminal shows that terminal at the pin (V4, 2026-10-02).
The bug: the terminal stood once per page, so a second pin there was a star branch naming it, and a replica served two pins at neither.
Fixed by layout-0108 and model-0220, every pin wired to a non-rail terminal shows the terminal at the pin, in every group."""

from typing import Any

import fransys as fr
import pytest
from _drawn_facts import symbol_subjects
from _drawn_pages import drawn_pages
from _model_build_cover import unit_document
from fransys.colours import BU

from fransys_model.vocab.tables import functions, items


def _feed(d: fr.Design, groups: list[str], *, coils: list[int], pin: str = "A1") -> dict[int, Any]:
    """Terminal X1:1 in group 0 fed by switch S1; relay K<n> in `groups[coils[n]]`.

    Each group is one `function` block, opened in the order its first device is made.
    """
    strip = d.terminal_strip("X1", "DEMO-TB-2.5-TWIN")
    opened: dict[int, Any] = {}
    terminal: Any = None
    psu: Any = None
    for number in sorted({0, *coils}):
        with d.function(groups[number], f"Group {number}") as opened[number]:
            if number == 0:
                switch = d.device("S1", "DEMO-SWITCH-2P")
                terminal = strip[1]
                d.series(switch.sw["B"], terminal.outer, wire=(BU, 0.5))
                psu = d.device("T1", "DEMO-PSU-24")
                d.ac_supply("MAINS", 230, psu.input["L"], n=psu.input["N"])
                d.dc_supply("S", psu)
                d.series(psu.output["+"], switch.sw["A"], wire=(BU, 0.5))
            for k, at in enumerate(coils, start=1):
                if at == number:
                    relay = d.device(f"K{k}", "DEMO-RLY-2CO-24")
                    d.series(terminal.inner, relay.coil[pin], wire=(BU, 0.5))
                    other = relay.coil["A1" if pin == "A2" else "A2"]
                    if number == 0:  # the coil's open pin returns to the 0 V rail, below it
                        d.series(other, psu.output["-"], wire=(BU, 0.5))
                    else:  # on a later page the open pin is fed from above, through a lamp, so the coil stands as before
                        lamp = d.device(f"H{k}", "DEMO-LAMP-24")
                        d.series(psu.output["+"], lamp.lamp[1], wire=(BU, 0.5))
                        d.series(lamp.lamp[2], other, wire=(BU, 0.5))
    return opened


def _one_relay(d: fr.Design, g: list[str]) -> None:
    _feed(d, g, coils=[1])


def _one_relay_fed_at_a2(d: fr.Design, g: list[str]) -> None:
    """The same relay fed at its other coil pin: the layout stands the coil unturned."""
    _feed(d, g, coils=[1], pin="A2")


def _two_relays_one_group(d: fr.Design, g: list[str]) -> None:
    _feed(d, g, coils=[1, 1])


def _two_relays_two_groups(d: fr.Design, g: list[str]) -> None:
    _feed(d, g, coils=[1, 2])


def _own_group(d: fr.Design, g: list[str]) -> None:
    _feed(d, g, coils=[0, 0])


def _built(plant) -> Any:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    plant(d, [f"G{i}" for i in range(3)])
    doc = unit_document(cab)
    return fr.build(d, doc).model


def _symbols(model, key: str) -> list[tuple[object, Any]]:
    """The (page, drawn symbol) pairs of library symbol `key`, on every page."""
    return [(page, s) for page, drawing in drawn_pages(model).items() for s in drawing.symbols if s.key == key]


def _drawn(model, name: str, tag: str = "") -> list[tuple[object, Any]]:
    """The (page, drawn symbol) pairs of function `name` of item `tag`, or of every terminal."""
    item_tag = {i.id: i.tag for i in items(model).values()}
    owned = {f.id.value for f in functions(model).values() if f.key[-1] == name and (not tag or item_tag.get(f.item, "") == tag)}
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
