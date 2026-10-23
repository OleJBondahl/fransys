"""The strings a drawn box carries for symdef to size and mark its symbol (el-0006).

A box has one row per port name, in drawing order. A contact table's texts are
`derive.coil_table_texts`. A plain library symbol has no texts.
"""

from typing import TYPE_CHECKING

from electrical_symbols import default_order, is_generic_box
from fransys_model.kernel import natural_key as kernel_key

if TYPE_CHECKING:
    from .placement_kit import Pick

__all__ = ["box_rows"]


def box_rows(pick: Pick) -> tuple[tuple[str, ...], ...]:
    """A generic box's texts, one port name per row in drawing order; none for another pick."""
    if not is_generic_box(pick.key):
        return ()
    return tuple((name,) for name in default_order(pick.ports.values(), kernel_key))
