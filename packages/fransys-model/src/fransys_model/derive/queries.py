"""Every read-only query Fransys's generators run.

See design/derive-queries.md and design/derive-queries-structure.md.

Each query lives in the module of its concern (`wiring`, `reports`, `structure`, `connectors`,
`plc_rack`); this module gathers them, as `derive.closure` gathers the net closure
(decisions 0019, 0021). `physical_nets` and `net_of` are in `closure.py`.
"""

from .black_box import drawing_set_is_replica_only, is_black_box_item
from .bom import TOP_LEVEL, bom_lines
from .connectors import connector_rows
from .document_unit import document_unit
from .harness import (
    cable_list_rows,
    cable_title,
    contents_rows,
    harness_cables,
    top_level_cables,
    unit_cable_page_key,
    unit_cables,
)
from .lookups import (
    effective_placement,
    item_description,
    item_location,
    list_context,
    no_conductor_at,
)
from .overview import overview_graph
from .plc_rack import is_plc_module, plc_rack_modules
from .release_order import release_order, same_version
from .reports import (
    cable_rows,
    core_colour,
    designation_list,
    plc_channel_rows,
    unit_boards,
    unit_strips,
    wire_rows,
)
from .revision_text import revision_text
from .revisions import current_revision, revision_history
from .structure import (
    board_netlist,
    boards,
    boundary,
    enclosing_boards,
    ext_usage,
    is_sole_unit_root,
    items_at,
    schematic_functions,
    standalone,
    subtree,
    unit_items,
    unit_subtree,
    units,
)
from .unit_release import unit_release
from .wiring import (
    conductors_on_item,
    first_leg,
    terminal_rows,
    terminal_strips,
    unconnected_ports,
    unused_terminals,
)

__all__ = [
    "TOP_LEVEL",
    "board_netlist",
    "boards",
    "bom_lines",
    "boundary",
    "cable_list_rows",
    "cable_rows",
    "cable_title",
    "conductors_on_item",
    "connector_rows",
    "contents_rows",
    "core_colour",
    "current_revision",
    "designation_list",
    "document_unit",
    "drawing_set_is_replica_only",
    "effective_placement",
    "enclosing_boards",
    "ext_usage",
    "first_leg",
    "harness_cables",
    "is_black_box_item",
    "is_plc_module",
    "is_sole_unit_root",
    "item_description",
    "item_location",
    "items_at",
    "list_context",
    "no_conductor_at",
    "overview_graph",
    "plc_channel_rows",
    "plc_rack_modules",
    "release_order",
    "revision_history",
    "revision_text",
    "same_version",
    "schematic_functions",
    "standalone",
    "subtree",
    "terminal_rows",
    "terminal_strips",
    "top_level_cables",
    "unconnected_ports",
    "unit_boards",
    "unit_cable_page_key",
    "unit_cables",
    "unit_items",
    "unit_release",
    "unit_strips",
    "unit_subtree",
    "units",
    "unused_terminals",
    "wire_rows",
]
