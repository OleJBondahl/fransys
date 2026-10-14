"""Render's own constants (grows as later parts of this work package add to it)."""

# How far the arrow's point is pulled in from the box's two near-edge corners, along the
# facing axis (render's own choice, unpinned by the spec): small relative to the box so the
# point reads as a spike, not a wedge.
MARKER_ARROW_DEPTH_G = 3

# A diagram box's text and tab margins, in G. They equal the layout engine's `TEXT_PAD`,
# `TEXT_LEAD` and `TAB_PAD` (diagram/sizes.py): render imports no layout constant (render-0009),
# so `tests/test_block_diagram_render.py` pins each to its layout twin and a mismatch fails there.
DIAGRAM_TEXT_PAD_G = 8
DIAGRAM_TEXT_LEAD_G = 4
DIAGRAM_TAB_PAD_G = 4

# A cut marker's arrow: its depth behind the line end, its half height, and the gap from the
# arrow tip to the text. Render's own choice; the layout reserves 24 G past the tip.
DIAGRAM_MARKER_DEPTH_G = 4
DIAGRAM_MARKER_HALF_G = 2
DIAGRAM_MARKER_GAP_G = 2
