"""Every finding code this repo emits, in one list (docs/design/geometry.md 5.4).

A stage code is defined in the stage that emits it, because `stages` may not import
`lint`; it is re-exported here so this module is the complete list. Codes are stable.
"""

from fransys_layout.stages.columns import (
    FUNCTION_UNPLACED_IN_COLUMN,
)
from fransys_layout.stages.partition import (
    GROUP_SPLIT,
    KEEP_TOGETHER_UNMET,
    ORDER_HINT_UNMET,
)
from fransys_layout.stages.place import PAGE_OVERFULL
from fransys_layout.stages.references import (
    JOIN_UNALIGNED,
    LINK_FANOUT,
    LINK_PARTNER_UNLOCATED,
    REFERENCE_BOX_EXCEEDS_ROOM,
)
from fransys_layout.stages.resolve import PIN_MAP_INCOMPLETE, SYMBOL_DEFAULTED
from fransys_layout.stages.route import ROUTE_FAILED
from fransys_layout.stages.texts.place_texts import LABEL_UNPLACED
from fransys_layout.stages.texts.power_lead import POWER_SYMBOL_UNPLACED

# lint/geometric.py (TEXT_CROSSED_BY_ROUTE and TEXT_OVERLAP in its private _texts.py), all WARNING
WIRE_NOT_ORTHOGONAL = "WIRE_NOT_ORTHOGONAL"
WIRE_THROUGH_SYMBOL = "WIRE_THROUGH_SYMBOL"
WIRE_OVER_LABEL = "WIRE_OVER_LABEL"
REDUNDANT_JOG = "REDUNDANT_JOG"
SYMBOL_OVERLAP = "SYMBOL_OVERLAP"
OUT_OF_CONTENT_BOX = "OUT_OF_CONTENT_BOX"
TEXT_CROSSED_BY_ROUTE = "TEXT_CROSSED_BY_ROUTE"
TEXT_OVERLAP = "TEXT_OVERLAP"

# lint/chains.py, both WARNING
LONE_CELL = "LONE_CELL"
CHAIN_BROKEN = "CHAIN_BROKEN"

# lint/coherence.py, all ERROR
CONNECTION_NOT_DRAWN = "CONNECTION_NOT_DRAWN"
CONNECTION_DRAWN_TWICE = "CONNECTION_DRAWN_TWICE"
ROUTE_WRONG_PORT = "ROUTE_WRONG_PORT"
ROUTE_SHORTS_NETS = "ROUTE_SHORTS_NETS"
MARKER_UNPAIRED = "MARKER_UNPAIRED"

# engines/schematic/read/ (`__init__.py`, `sheets.py`), both WARNING. Defined here, imported there,
# because `lint` may not import `engines`.
SHEET_FORMAT_UNUSED = "SHEET_FORMAT_UNUSED"
CONNECTION_TO_UNDRAWN = "CONNECTION_TO_UNDRAWN"

ALL_CODES: tuple[str, ...] = (
    CHAIN_BROKEN,
    CONNECTION_DRAWN_TWICE,
    CONNECTION_NOT_DRAWN,
    CONNECTION_TO_UNDRAWN,
    FUNCTION_UNPLACED_IN_COLUMN,
    GROUP_SPLIT,
    JOIN_UNALIGNED,
    KEEP_TOGETHER_UNMET,
    LABEL_UNPLACED,
    LINK_FANOUT,
    LINK_PARTNER_UNLOCATED,
    LONE_CELL,
    MARKER_UNPAIRED,
    ORDER_HINT_UNMET,
    OUT_OF_CONTENT_BOX,
    PAGE_OVERFULL,
    PIN_MAP_INCOMPLETE,
    POWER_SYMBOL_UNPLACED,
    REDUNDANT_JOG,
    REFERENCE_BOX_EXCEEDS_ROOM,
    ROUTE_FAILED,
    ROUTE_SHORTS_NETS,
    ROUTE_WRONG_PORT,
    SHEET_FORMAT_UNUSED,
    SYMBOL_DEFAULTED,
    SYMBOL_OVERLAP,
    TEXT_CROSSED_BY_ROUTE,
    TEXT_OVERLAP,
    WIRE_NOT_ORTHOGONAL,
    WIRE_OVER_LABEL,
    WIRE_THROUGH_SYMBOL,
)
