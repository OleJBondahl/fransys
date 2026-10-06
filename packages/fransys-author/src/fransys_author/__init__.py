"""Fransys input: the authoring engine under the `fr.design` surface (spec R11).

Worked example::

    import fransys as fr
    import fransys_author
    parts = fr.parts("demo_parts")
    d = fransys_author.Design(parts)
    d.project(title="Pump station", number="P-1001", customer="Example Co",
              revision=1, author="OJB")
    d.revision(1, date="2026-09-21", text="First issue", created="OJB")
    c1 = d.location("C1", "Pump cabinet")
    sup = d.group("SUP", "24 V supply")
    q1 = d.item("DEMO-MCB-C6", tag="Q1", at=c1, group=sup)
    draft = d.draft()
"""

from fransys_model.vocab import Operating, Rating

from .design import Design, Scope
from .errors import AuthorError
from .handles import Cable, Fn, Group, Item, Location, Port, Strip, Terminal
from .wiring import Wiring

__all__ = [
    "AuthorError",
    "Cable",
    "Design",
    "Fn",
    "Group",
    "Item",
    "Location",
    "Operating",
    "Port",
    "Rating",
    "Scope",
    "Strip",
    "Terminal",
    "Wiring",
]
