"""G3 (layout-0077): two rack bugs, each with a demo-parts model that raised before the fix.

A rack module's column key carried its integer `position`. On a page with no group the column
key becomes the `Page` key, whose segments must be `str`, so layout raised `SchemaError`
("authoring key ... is not a tuple of str"). The rack sits at a location, its modules carry no
`at=` and no `group=`, so their page has no group.

1. The integer position must sort as a number, and the key must hold only strings.
2. Rack items with no group lay out like any other ungrouped item.

Layout never raises for a model with no ERROR, so each test also asserts where it put the modules.
"""

from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
from _drawn_pages import drawn_pages
from _model_build_cover import layout_trigger_document

_PROJECT: dict[str, Any] = {
    "title": "Rack keys",
    "number": "P-1003",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}


def _ungrouped_rack_x(do_position: int, di_position: int) -> dict:
    """Column x of the DO and DI modules of a rack whose modules have no location and no group."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-25", text="First issue", created="XX")
    rack = d.item(None, tag="U1", at=d.location("C1", "Cabinet"))
    do = d.item("DEMO-PLC-DO-2", tag="DO1", name="do", parent=rack, position=do_position)
    di = d.item("DEMO-PLC-DI-2", tag="DI1", name="di", parent=rack, position=di_position)
    k1 = d.item("DEMO-RLY-2CO-24", tag="K1")
    k2 = d.item("DEMO-RLY-2CO-24", tag="K2")
    wire = d.wiring(colour="BU", gauge="0.5")
    wire(do.fn("do_1")["1"], k1.fn("coil")["A1"])
    wire(di.fn("di_1")["1"], k2.fn("co_1")["14"])
    model = fr.build(parts, d.draft(), layout_trigger_document()).model
    x = {}
    for drawing in drawn_pages(model).values():
        for symbol in drawing.symbols:
            for name, _ in symbol.slots:
                module = name.removeprefix("marking.").split("_")[0]
                if symbol.key == "generic-box" and module in {"do", "di"}:
                    x[(module,)] = symbol.x
    return x


def test_an_integer_position_orders_the_modules_as_a_number() -> None:
    # as text, "10" would sort before "9": the DI module (9) must stand left of the DO module (10)
    x = _ungrouped_rack_x(do_position=10, di_position=9)
    assert x[("di",)] < x[("do",)]


def test_rack_items_with_no_group_are_laid_out_in_position_order() -> None:
    x = _ungrouped_rack_x(do_position=1, di_position=2)
    assert set(x) == {("do",), ("di",)}
    assert x[("do",)] < x[("di",)]
