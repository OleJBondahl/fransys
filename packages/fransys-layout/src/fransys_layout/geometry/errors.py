"""Layout errors: structural problems, raised and never silenced.

Layout problems of a half-finished design are not here: a stage returns a kernel
`Finding` instead of raising.
"""

from fransys_model.kernel import ModelError


class LayoutError(ModelError):
    """Base of everything this repo raises."""


class GeometryError(LayoutError):
    """A library coordinate is off the drawing grid (0.125 M), or a box has a negative size."""
