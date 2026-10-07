"""Fixtures of `test_ratings_acceptance.py` (RATINGS-1 step 2, acceptance 5): demo parts only.

A design over the demo parts with the 400 V supply declared, the record helpers that give a demo
part's function template another rating for one test, and the three plants of the spec: a line
motor behind a contactor, a changeover's common, and a reversing starter.
"""

import dataclasses
from decimal import Decimal
from typing import TYPE_CHECKING

import fransys_parts
from fransys_author import Design, Item

from fransys_model.kernel import Id, Model, Origin, evolve, freeze, make_id, merge
from fransys_model.vocab.facets.rating import RatingFacet
from fransys_model.vocab.ratings import Rating
from fransys_model.vocab.tables import facets_of, function_templates, parts

if TYPE_CHECKING:
    from collections.abc import Callable

    from fransys_author import Port

    from fransys_model.vocab.templates import FunctionTemplate

RAILS = {"L1": ("230", 0), "L2": ("230", 120), "L3": ("230", 240), "N": ("0", None)}
_ORIGIN = Origin(file="tests/ratings_fixtures.py", line=1, note="")


def design(earthing: str = "earthed") -> tuple[Design, Callable[[Port, Port], None]]:
    """A design over the demo parts with the 400 V supply declared, and a wire maker."""
    d = Design(fransys_parts.load("demo_parts"))
    d.supply("400V", current="ac", rails=RAILS, earthing=earthing)
    return d, d.wiring(colour="BK", gauge="1.5")


def freeze_design(d: Design) -> Model:
    return freeze(merge(fransys_parts.load("demo_parts"), d.draft()))


def template_of(model: Model, mpn: str, function: str) -> FunctionTemplate:
    """The function template `function` of the part `mpn`."""
    part = next(p for p in parts(model).values() if p.mpn == mpn)
    return next(
        t for t in function_templates(model).values() if t.part == part.id and t.name == function
    )


def rating_facet(template: FunctionTemplate, **fields: str) -> RatingFacet:
    """A `RatingFacet` of `template` whose `Rating` fields are the given decimals."""
    key = ("test", "rating", *template.key)
    rating = dataclasses.replace(Rating(), **{name: Decimal(text) for name, text in fields.items()})
    return RatingFacet(id=make_id(RatingFacet, key), key=key, subject=template.id, rating=rating)


def rated(model: Model, mpn: str, function: str, **fields: str) -> Model:
    """`model` with the function template of `mpn` rated `fields`, replacing any rating it had."""
    template = template_of(model, mpn, function)
    old = [f.id for f in facets_of(model, RatingFacet).values() if f.subject == template.id]
    return evolve(model, remove=old, put=[rating_facet(template, **fields)], origin=_ORIGIN)


def lamp_on(d: Design, *potentials: str) -> Item:
    """A lamp `h1` whose port 1, then port 2, is on a declared net of the given potential."""
    lamp = d.item("DEMO-LAMP-24", name="h1")
    for port, potential in zip(("1", "2"), potentials, strict=False):
        d.net(potential, lamp[port], cls="power", potential=potential)
    return lamp


def fn_id(item: Item, name: str) -> Id:
    return item.fn(name).id


def line_motor() -> tuple[Model, dict]:
    """L1, L2, L3 into contactor Q1 (1, 3, 5), then one MCB per phase, then the motor's U, V, W."""
    d, wire = design()
    q1 = d.item("DEMO-CTR-3P-24", name="q1")
    fuses = [d.item("DEMO-MCB-C6", name=f"f{n}") for n in (1, 2, 3)]
    m1 = d.item("DEMO-MOTOR-4KW", name="m1")
    main = q1.fn("main")
    for rail, pole in (("L1", "1"), ("L2", "3"), ("L3", "5")):
        d.net(rail, main[pole], cls="power", potential=rail)
    for out, fuse, motor_pole in (("2", fuses[0], "U"), ("4", fuses[1], "V"), ("6", fuses[2], "W")):
        wire(main[out], fuse["1"])
        wire(fuse["2"], m1[motor_pole])
    return freeze_design(d), {"q1": q1, "m1": m1}


def changeover_lamp() -> tuple[Model, dict]:
    """Contact `co_1` of a relay with 12 on L1 and 14 on L2, its common 11 wired to a lamp on N."""
    d, wire = design()
    contact = d.item("DEMO-RLY-2CO-24", name="k1").fn("co_1")
    d.net("L1", contact["12"], cls="power", potential="L1")
    d.net("L2", contact["14"], cls="power", potential="L2")
    lamp = d.item("DEMO-LAMP-24", name="h1")
    d.net("N", lamp["2"], cls="power", potential="N")
    wire(contact["11"], lamp["1"])
    return freeze_design(d), {"lamp": lamp}


def reversing_starter(*, reverse: bool = False) -> tuple[Model, dict]:
    """K1: L1 to U, L3 to W; K2: L1 to W, L3 to U; the motor's V on L2 through both; a lamp on
    L1 and N; a second lamp `h2` bridges K1's and K2's port 1, so both ends are on L1 (no pair
    stands across it) unless L3 leaks through the starter into the L1 net. `reverse` declares
    everything after the items in the opposite order."""
    d, wire = design()
    names = [
        ("k1", "DEMO-CTR-3P-24"),
        ("k2", "DEMO-CTR-3P-24"),
        ("m1", "DEMO-MOTOR-4KW"),
        ("h1", "DEMO-LAMP-24"),
        ("h2", "DEMO-LAMP-24"),
    ]
    items = {name: d.item(mpn, name=name) for name, mpn in (reversed(names) if reverse else names)}
    k1, k2 = items["k1"].fn("main"), items["k2"].fn("main")
    m1, h1, h2 = items["m1"], items["h1"], items["h2"]
    steps: list[Callable[[], None]] = [
        lambda: d.net("L1", k1["1"], k2["1"], h1["1"], cls="power", potential="L1"),
        lambda: d.net("L2", k1["3"], k2["3"], cls="power", potential="L2"),
        lambda: d.net("L3", k1["5"], k2["5"], cls="power", potential="L3"),
        lambda: d.net("N", h1["2"], cls="power", potential="N"),
        lambda: wire(k1["2"], m1["U"]),
        lambda: wire(k1["4"], m1["V"]),
        lambda: wire(k1["6"], m1["W"]),
        lambda: wire(k2["2"], m1["W"]),
        lambda: wire(k2["4"], m1["V"]),
        lambda: wire(k2["6"], m1["U"]),
        lambda: wire(k1["1"], h2["1"]),
        lambda: wire(k2["1"], h2["2"]),
    ]
    for step in reversed(steps) if reverse else steps:
        step()
    return freeze_design(d), {"m1": m1, "h1": h1, "h2": h2}
