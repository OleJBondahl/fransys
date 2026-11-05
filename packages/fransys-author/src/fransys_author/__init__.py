"""Fransys input: the authoring engine under the `fr.design` surface.

Worked example::

    import fransys as fr
    from fransys_author.design import Design
    parts = fr.parts("demo_parts")
    d = Design(parts)
    d.project(title="Pump station", number="P-1001", customer="Example Co",
              revision=1, author="OJB")
    d.revision(1, date="2026-09-21", text="First issue", created="OJB")
    c1 = d.location("C1", "Pump cabinet")
    sup = d.group("SUP", "24 V supply")
    q1 = d.item("DEMO-MCB-C6", tag="Q1", at=c1, group=sup)
    draft = d.draft()
"""

from fransys_model.vocab import Operating

from ._origin import caller_origin
from .errors import AuthorError
from .surface._rows import RowValue, WiringRow

__all__ = ["AuthorError", "Operating", "RowValue", "WiringRow", "caller_origin"]
