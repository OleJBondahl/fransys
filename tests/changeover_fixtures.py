"""Fixture of `test_changeover_rail_pairs.py` (CONTACT-STATES acceptance 1 and 2): demo parts only.

Two independent IT supplies, `MAIN` (`M_L1..M_L3` and `M_N`) and `EMERG` (`E_L1..E_L3`, no
neutral), a four-pole changeover `q1` that puts MAIN on its make throws and EMERG on its break
throws, a two-pole breaker `f1` in series with bus lines 1 and 4, and a power supply `t1` whose
input is rated 264 V AC. Pole 4 takes `M_N` on its make throw and `E_L3` on its break throw.

EMERG is a 230 V line-to-line supply: its phases stand at 133 V, and 133 V * sqrt(3) is about 230 V.
Without state-awareness a bus line carries one MAIN and one EMERG rail, and the check pairs them at
398.4 V (MAIN's voltage to earth) + 230.4 V (EMERG's), about 628.8 V.
"""

import dataclasses

import fransys_parts
from fransys_author import Design

from fransys_model.kernel import Model, Origin, evolve, freeze, merge
from fransys_model.vocab.enums import PortRole
from fransys_model.vocab.tables import function_templates, parts, port_templates

MAIN = {"M_L1": ("230", 0), "M_L2": ("230", 120), "M_L3": ("230", 240), "M_N": ("0", None)}
EMERG = {"E_L1": ("133", 0), "E_L2": ("133", 120), "E_L3": ("133", 240)}
_ORIGIN = Origin(file="tests/changeover_fixtures.py", line=1, note="")
_MPN = "DEMO-CO-4P-24"


def _on(d: Design, potential: str, *ports) -> None:
    d.net(potential, *ports, cls="power", potential=potential)


def changeover_bus(*, throw_roles: bool = True) -> tuple[Model, dict]:
    """The case above; `throw_roles=False` gives every changeover port the role `generic`.

    The control: with no throw roles no link has a state, so the case is the both-closed
    reading that gave the false finding. Returns the model and the items `q1`, `f1`, `t1`.
    """
    d = Design(fransys_parts.load("demo_parts"))
    d.supply("MAIN", current="ac", rails=MAIN, earthing="it")
    d.supply("EMERG", current="ac", rails=EMERG, earthing="it")
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
    """`model` with every port template of the changeover part set to `PortRole.GENERIC`."""
    part = next(p for p in parts(model).values() if p.mpn == _MPN)
    templates = {t.id for t in function_templates(model).values() if t.part == part.id}
    swapped = [
        dataclasses.replace(t, role=PortRole.GENERIC)
        for t in port_templates(model).values()
        if t.function in templates
    ]
    return evolve(model, remove=[t.id for t in swapped], put=swapped, origin=_ORIGIN)
