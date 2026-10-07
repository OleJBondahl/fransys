"""An invented board and PLC rack, built with raw part/item records through `fr.build`
(facade WP: F4 and F6's board/rack legs). `examples/demo-parts` carries no `[pcb]`-faceted
part and neither root fixture uses a PLC module, so `connectors-*.csv`, `wago-*.xml`,
`netlist-*.net` and `fransys_kicad.check` are otherwise unexercisable from the two pinned
fixtures (whose `core`/`facet` digests must not move, spec F9). Every part, MPN and
designation here is invented (CLAUDE.md invariant 6), following the pattern of
`packages/fransys-kicad/tests/conftest.py` and `packages/fransys-wago/tests/conftest.py`.

One `Function` record in this model, directly on `board_item` (render work order, PART 5b,
model-0039): it proves `schematic_functions(model)` correctly excludes a real board-mounted
function (the board exclusion covers the board item's own leaf, not only its descendants --
see `structure.schematic_functions`'s docstring), so `fransys_render.check`'s
`LAYOUT_MISSING` -- which now fires on `schematic_functions(model)`, not every `Function`
record -- correctly stays quiet even though a `Function` record exists, for a genuine
board/rack-only submission built through the real pipeline (`fr.build`, not a hand-frozen
`Draft`). `test_acceptance.py::test_board_and_rack_model_has_no_layout_missing_finding` is
the can-fail proof of this. The module's channel content (a `FunctionTemplate` +
`PlcChannelFacet` naming a real `Function`) is exactly what
`packages/fransys-wago/tests/conftest.py`'s own fixtures already exercise; this facade-
level fixture only needs to prove F6's naming/routing, which a channel-less module still
does (`fransys_wago.modules.modules_xml`'s own `if not module.channels: continue` skips
the module's `<Module>` element but the rack still writes a `wago-R1.xml`, and
`fransys._subjects.racks` finds `R1` by its module's `PartCategory.PLC_MODULE`, never by
any `Function`).
"""

import fransys as fr
from _model_build_cover import layout_trigger_document, system_document

from fransys_model.kernel import Draft, Model, Origin, make_id
from fransys_model.vocab.core import Function, Item
from fransys_model.vocab.enums import FunctionKind, PartCategory
from fransys_model.vocab.facets.pcb import PcbFacet
from fransys_model.vocab.templates import Part

_ORIGIN = Origin(file="packages/fransys/tests/_board_and_rack.py", line=1, note="invented")


def build_board_and_rack_model(*, lays_out: bool = False) -> Model:
    """A board `PCB1` (one function of its own) and a PLC rack `R1` with one (channel-less)
    module, via `fr.build`; `lays_out` keeps a SCHEMATIC page so the layout call runs.
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
        template=None,
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
            board_item,
            board_function,
            module_part,
            rack_item,
            module_item,
        ],
        origin=_ORIGIN,
    )
    document = layout_trigger_document() if lays_out else system_document()
    return fr.build(draft, document).model
