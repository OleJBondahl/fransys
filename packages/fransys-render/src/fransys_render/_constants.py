"""Render's own constants (grows as later parts of this work package add to it)."""

from decimal import Decimal

# A typical EE-schematic line weight. Render's own choice: D11 pins units (mm) but not a
# value, so nothing in the spec derives this number.
STROKE_WIDTH_MM = Decimal("0.25")

# A junction dot a little larger than the line it sits on. Render's own choice, unpinned by
# the spec (D8: "the dot's diameter is a render constant"), the same way STROKE_WIDTH_MM is.
JUNCTION_DOT_DIAMETER_MM = Decimal(1)

# The Liberation Serif Regular 2.1.5 typographic ascent ratio (D7): OS/2.sTypoAscender / unitsPerEm
# = 1420 / 2048, read with fontTools 4.65.0 from the same font file fransys_layout's
# text_metrics.py table was built from (sha256
# 058ea80864aef09a23f45cbec2bb5400bc3dfbdea01c3f10538a21fcb497fb74, cited there). Exact
# because 2048 = 2**11: no rounding.
ASCENT_RATIO = Decimal(1420) / Decimal(2048)

# How far the arrow's point is pulled in from the box's two near-edge corners, along the
# facing axis (render's own choice, unpinned by the spec, the same way STROKE_WIDTH_MM
# is): small relative to the box so the point reads as a spike, not a wedge.
MARKER_ARROW_DEPTH_G = 3

# The dash-dot outline's long dash and the gap on either side of its dot (IEC 60617's
# boundary-line convention: long dash, gap, dot, gap, repeating). Render's own choice of
# lengths, unpinned by the spec, the same way STROKE_WIDTH_MM is: the dot itself is not
# a third constant here, it is exactly one `STROKE_WIDTH_MM` long -- a dash that short
# reads as a dot rather than a second short dash, the classic dash-dot proportion.
OUTLINE_DASH_LONG_MM = Decimal(4)
OUTLINE_DASH_GAP_MM = Decimal(1)

# A diagram box's text and tab margins, in G. They equal the layout engine's `TEXT_PAD`,
# `TEXT_LEAD` and `TAB_PAD` (diagram/sizes.py): render imports no layout constant (render-0009),
# so `tests/test_block_diagram_render.py` pins each to its layout twin and a mismatch fails there.
DIAGRAM_TEXT_PAD_G = 8
DIAGRAM_TEXT_LEAD_G = 4
DIAGRAM_TAB_PAD_G = 4

# A cut marker's arrow: its depth behind the line end, its half height, and the gap from the
# arrow tip to the text. Render's own choice; the layout reserves 24 G past the tip (BD5).
DIAGRAM_MARKER_DEPTH_G = 4
DIAGRAM_MARKER_HALF_G = 2
DIAGRAM_MARKER_GAP_G = 2
