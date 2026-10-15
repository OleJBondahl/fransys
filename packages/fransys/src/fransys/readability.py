"""`readability`: how readable the schematic pages of a build are (decision 0182)."""

from fransys_el import OPTIONS

from fransys_layout import page_readability
lazy from fransys_model.derive import ReadabilityReport

lazy from .pipeline import BuildResult


def readability(result: BuildResult) -> ReadabilityReport:
    """Read: one row for each schematic page of `result`, and one for each unit.

    A page row counts what a reader of the print feels: the profile's text height against
    `min_text_height_mm`, how much of the page the drawing fills, wires crossing wires, text struck
    by a wire, text overlaps, cells alone on a page, and the references the page makes. A unit row
    adds its pages up. Pure: the same model gives the same rows. The layout runs again on
    `result.model`, as `build` ran it, so the cost is about that of the layout.

    Does not write a file, emit anything from `write`, or raise on findings.
    """
    return page_readability(result.model, OPTIONS)
