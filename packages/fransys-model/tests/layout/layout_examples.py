"""Invented layout records shared by the layout tests."""

from decimal import Decimal
from typing import TYPE_CHECKING

from fransys_model.kernel import Id
from fransys_model.layout import (
    DrawingSet,
    Orientation,
    Page,
    PageGroup,
    PageRole,
    SheetFormat,
    SymbolPlacement,
)
from fransys_model.vocab.aspects import AspectNode
from fransys_model.vocab.core import Function, Item
from fransys_model.vocab.enums import Aspect, FunctionKind

if TYPE_CHECKING:
    from fransys_model.vocab.templates import FunctionTemplate

PRODUCED_BY = "example-engine 0.0.0"

# design/layout-namespace.md: a drawing set is keyed by its engine, its kind and its location
# (`unlocated` here); a page by its drawing set, its first group, its role and an ordinal that is 0
# unless split.
DRAWING_SET_KEY = ("layout", "example-engine", "drawing_set", "unlocated")
PAGE_KEY = (*DRAWING_SET_KEY, "examples", "function", "pump1", "power", "0")


def function_id(value: str) -> Id[Function]:
    """A function id made of one repeated hex digit."""
    return Id(kind="function", value=value * 32)


def template_id(value: str) -> Id[FunctionTemplate]:
    """A function-template id made of one repeated hex digit."""
    return Id(kind="function_template", value=value * 32)


def group_node() -> AspectNode:
    """The invented `=PUMP1` function-aspect node."""
    return AspectNode(
        id=Id(kind="aspect_node", value="a" * 32),
        key=("examples", "function", "pump1"),
        aspect=Aspect.FUNCTION,
        parent=None,
        label="PUMP1",
        description="Invented pump 1",
    )


def drawn_function() -> tuple[Item, Function]:
    """One invented part-less item with one contact function."""
    item = Item(
        id=Id(kind="item", value="b" * 32),
        key=("examples", "pump1", "contactor"),
        part=None,
        parent=None,
        position=None,
        tag="K1",
        description="Invented contactor",
    )
    function = Function(
        id=function_id("c"),
        key=("examples", "pump1", "contactor", "fn", "main"),
        item=item.id,
        template=None,
        name="main",
        kind=FunctionKind.CONTACT_NO,
    )
    return item, function


def sheet_format() -> SheetFormat:
    """The invented A3 landscape sheet."""
    return SheetFormat(
        id=Id(kind="layout.sheet_format", value="d" * 32),
        key=("examples", "layout", "a3"),
        name="A3 landscape",
        width_mm=420,
        height_mm=297,
        content_x_mm=10,
        content_y_mm=10,
        content_width_mm=400,
        content_height_mm=277,
        frame_columns=8,
        frame_rows=6,
        module_mm=Decimal("2.5"),
    )


def drawing_set() -> DrawingSet:
    """One drawing set without a location."""
    return DrawingSet(
        id=Id(kind="layout.drawing_set", value="e" * 32),
        key=DRAWING_SET_KEY,
        location=None,
        number=1,
        produced_by=PRODUCED_BY,
    )


def page() -> Page:
    """Page 1 of `drawing_set()`, drawing the `=PUMP1` group."""
    return Page(
        id=Id(kind="layout.page", value="f" * 32),
        key=PAGE_KEY,
        drawing_set=drawing_set().id,
        number=1,
        role=PageRole.POWER,
        sheet_format=sheet_format().id,
        groups=(PageGroup(group=group_node().id, index=0),),
        produced_by=PRODUCED_BY,
    )


def placement(*, x: int = 64) -> SymbolPlacement:
    """The contact of `drawn_function()` placed on `page()` at (`x`, 96)."""
    return SymbolPlacement(
        id=Id(kind="layout.symbol_placement", value="9" * 32),
        key=("layout", "example-engine", "symbol_placement", "examples", "pump1", "contactor"),
        function=function_id("c"),
        page=page().id,
        x=x,
        y=96,
        orientation=Orientation.R0,
        poles=3,
        symbol="make-contact",
        library_version="0.1.0",
        produced_by=PRODUCED_BY,
    )
