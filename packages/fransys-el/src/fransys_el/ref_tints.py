"""`REF_TINTS`: the eight net-reference fill tints, in slot order (el-0001, REF-COLOURS C3).

The values are ruled (OKLab L 0.86, chroma up to 0.10, hues 45 degrees apart); the test
checks the floor: L of at least 0.85 and black text at 7:1 or better.
"""

REF_TINTS: tuple[str, ...] = (
    "#ffc0aa",
    "#85e7cd",
    "#e4c0ff",
    "#efcc83",
    "#80e1fe",
    "#ffbad4",
    "#bbdf99",
    "#bbd1ff",
)
