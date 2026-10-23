"""Names of the pack-row solver nodes: the one home of the node-id strings (CORE-CLEAN-3B B3).

A node name is a prefix, the id it stands for and, for an extent, an end. Writers and
readers of the x and y solvers call these functions and never type a prefix.
"""

from __future__ import annotations

LOW = "L"
HIGH = "R"

SLOT = "slot:"
BOX = "box:"
PIN = "pin:"
COL = "col:"


def slot_node(block: str, end: str) -> str:
    """The `end` (`LOW` or `HIGH`) of a block's slot."""
    return f"{SLOT}{block}:{end}"


def box_node(box: str, end: str) -> str:
    """The `end` (`LOW` or `HIGH`) of a box in the x solver."""
    return f"{BOX}{box}:{end}"


def box_y_node(box: str) -> str:
    """A box in the y solver."""
    return f"{BOX}{box}"


def pin_node(box: str, pin: str) -> str:
    """A pin of a box."""
    return f"{PIN}{box}:{pin}"


def col_node(col: str) -> str:
    """A column."""
    return f"{COL}{col}"
