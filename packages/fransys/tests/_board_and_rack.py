"""An invented board and PLC rack, built with raw part/item records through `fr.build`
(the board and rack legs of the facade's build). `examples/demo-parts` carries no `[pcb]`-faceted
part and neither root fixture uses a PLC module, so `connectors-*.csv`, `wago-*.xml`,
"""

import fransys as fr
from _model_build_cover import system_document

from fransys_model.kernel import Draft, Model, Origin, make_id
from fransys_model.vocab.core import Function, Item
from fransys_model.vocab.enums import FunctionKind, PartCategory
from fransys_model.vocab.facets.pcb import PcbFacet
from fransys_model.vocab.templates import FunctionTemplate, Part

_ORIGIN = Origin(file="packages/fransys/tests/_board_and_rack.py", line=1, note="invented")


def build_board_and_rack_model() -> Model:
    """A board `PCB1` (one function of its own) and a PLC rack `R1` with one (channel-less)
    module, via `fr.build`.
    """
    board_part = Part(
        id=make_id(Part, ("board",)),
        key=("board",),
        mpn="SIM-BOARD-DEMO",
        manufacturer="Example Co",
        description="Invented board",
        category=PartCategory.BOARD,
        class_code="A",
    )
    board_pcb = PcbFacet(
        id=make_id(PcbFacet, ("board", "pcb")),
        key=("board", "pcb"),
        subject=board_part.id,
        revision="A",
    )
    board_template = FunctionTemplate(
        id=make_id(FunctionTemplate, ("board", "fn")),
        key=("board", "fn"),
        part=board_part.id,
        name="fn",
        kind=FunctionKind.GENERIC,
    )
    board_item = Item(
        id=make_id(Item, ("board-item",)),
        key=("board-item",),
        part=board_part.id,
        parent=None,
        position=None,
        tag="PCB1",
        description="Invented board",
    )
    board_function = Function(
        id=make_id(Function, ("board-item", "fn")),
        key=("board-item", "fn"),
        item=board_item.id,
        template=board_template.id,
        name="fn",
        kind=FunctionKind.GENERIC,
    )

    module_part = Part(
        id=make_id(Part, ("module",)),
        key=("module",),
        mpn="SIM-DI-2CH",
        manufacturer="Example Co",
        description="Invented 2-channel digital input",
        category=PartCategory.PLC_MODULE,
        class_code="A",
    )
    rack_item = Item(
        id=make_id(Item, ("rack",)),
        key=("rack",),
        part=None,
        parent=None,
        position=None,
        tag="R1",
        description="Invented rack",
    )
    module_item = Item(
        id=make_id(Item, ("module-item",)),
        key=("module-item",),
        part=module_part.id,
        parent=rack_item.id,
        position=0,
        tag="A1",
        description="Invented module",
    )
    draft = Draft()
    draft.extend(
        [
            board_part,
            board_pcb,
            board_template,
            board_item,
            board_function,
            module_part,
            rack_item,
            module_item,
        ],
        origin=_ORIGIN,
    )
    return fr.build(draft, system_document()).model
