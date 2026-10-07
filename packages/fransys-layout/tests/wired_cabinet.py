"""The cabinet with its cable `W1`'s two cores redrawn as plain wires (HL1 off for `W1`).

HL1 draws `W1` (two cores, rails to lamp `-H1`) as a harness line, so the lamp's pins no longer
pick their sides from wires and the rail star loses its `-H1` branch. Tests whose rule needs that
geometry (a widened generic box, a branch marker beside a sibling lane, a text-shrunk page room)
build this variant instead: the same records, `W1`'s cores turned into wires.
"""

import dataclasses

from layout_cabinet import build_cabinet

from fransys_model.kernel import Draft, make_id
from fransys_model.vocab import Conductor, ConductorKind, CoreFacet, Item

_W1 = make_id(Item, ("cabinet", "w1"))


def wired_cabinet(**options: bool) -> Draft:
    """`build_cabinet(**options)` with `W1`'s cores as wires: no carrier, no core facet."""
    draft = build_cabinet(**options)
    cores = {r.id for r in draft.records() if isinstance(r, Conductor) and r.carrier == _W1}
    out = Draft()
    for record in draft.records():
        if isinstance(record, CoreFacet) and record.subject in cores:
            continue
        origin = draft.origin_of(record.id)
        assert origin is not None
        if isinstance(record, Conductor) and record.id in cores:
            out.add(
                dataclasses.replace(record, kind=ConductorKind.WIRE, carrier=None), origin=origin
            )
        else:
            out.add(record, origin=origin)
    return out
