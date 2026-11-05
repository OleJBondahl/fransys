"""Fixture of `test_changeover_rail_pairs.py`: demo parts only.

Two independent supplies, `MAIN` (`M_L1..M_L3` and `M_N`) and `EMERG` (`E_L1..E_L3`, no
neutral), a relay `q1` with four changeover contacts that puts MAIN on its make throws and
"""

import dataclasses
from typing import Any

import fransys_parts
from fransys_author.design import Design
from root_library import freeze

from fransys_model.kernel import Model, Origin, evolve, merge
from fransys_model.vocab.enums import PortBoundary
from fransys_model.vocab.tables import function_templates, parts, port_templates

MAIN = {"M_L1": ("230", 0), "M_L2": ("230", 120), "M_L3": ("230", 240), "M_N": ("0", None)}
EMERG = {"E_L1": ("133", 0), "E_L2": ("133", 120), "E_L3": ("133", 240)}
_ORIGIN = Origin(file="tests/changeover_fixtures.py", line=1, note="")
_MPN = "DEMO-RLY-4CO-24"


def _on(d: Design, potential: str, *ports) -> None:
    d.net(potential, *ports, cls="power", potential=potential)


def changeover_bus(*, throw_roles: bool = True) -> tuple[Model, dict[Any, Any]]:
    """The case above; `throw_roles=False` gives every changeover port the role `generic`.

    The control: with no throw roles no link has a state, so the case is the both-closed
    reading that gave the false finding. Returns the model and the items `q1`, `f1`, `t1`.
    """
    d = Design(fransys_parts.load("demo_parts"))
    d.supply("MAIN", current="ac", rails=MAIN)
    d.supply("EMERG", current="ac", rails=EMERG)
    wire = d.wiring(colour="BK", gauge="1.5")
    q1 = d.item(_MPN, name="q1")
    f1 = d.item("DEMO-MCB-2P", name="f1")
    t1 = d.item("DEMO-PSU-24", name="t1")
    pole = {n: q1.fn(f"co_{n}") for n in (1, 2, 3, 4)}
    for n in (1, 2, 3):
        _on(d, f"M_L{n}", pole[n][f"{n}4"])
    for n in (1, 2):
        _on(d, f"E_L{n}", pole[n][f"{n}2"])
    _on(d, "M_N", pole[4]["44"])
    _on(d, "E_L3", pole[3]["32"], pole[4]["42"])
    wire(pole[1]["11"], f1.fn("pole_1")["1"])
    wire(pole[4]["41"], f1.fn("pole_2")["3"])
    wire(f1.fn("pole_1")["2"], t1.fn("input")["L"])
    wire(f1.fn("pole_2")["4"], t1.fn("input")["N"])
    model = freeze(merge(fransys_parts.load("demo_parts"), d.draft()))
    if not throw_roles:
        model = _without_throw_roles(model)
    return model, {"q1": q1, "f1": f1, "t1": t1}


def _without_throw_roles(model: Model) -> Model:
    """`model` with every port template of the changeover part set to `PortBoundary.GENERIC`."""
    part = next(p for p in parts(model).values() if p.mpn == _MPN)
    templates = {t.id for t in function_templates(model).values() if t.part == part.id}
    swapped = [
        dataclasses.replace(t, boundary=PortBoundary.GENERIC, pin_role=None) for t in port_templates(model).values() if t.function in templates
    ]
    return evolve(model, remove=[t.id for t in swapped], put=swapped, origin=_ORIGIN)
