"""`readability`: how readable the drawn schematic pages of a build are (el-0043, R218)."""

import fransys_el

lazy from fransys_model.derive import DrawnReading

lazy from .pipeline import BuildResult


def readability(result: BuildResult) -> DrawnReading:
    """Read: one row of counts for each page drawn in `result.drawings`, in their order.

    A page row counts its symbols, markers, wire crossings, bends and length, texts struck by a wire
    and text overlaps. An error build has no drawings and gives no rows. Pure.

    Does not write a file, lay the pages out again or raise on findings.
    """
    return fransys_el.readability(result.drawings)
