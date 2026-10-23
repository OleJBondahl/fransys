"""Row shapes of `derive.footprints`: a box in grid units and a symbol's two footprints."""

from fransys_model.kernel import value

__all__ = ["Extent", "Footprints"]


@value
class Extent:
    """A box in G, in the frame of the symbol's body: top-left `x`, `y` and its size."""

    x: int
    y: int
    width: int
    height: int


@value
class Footprints:
    """The room a symbol takes: `standalone`, and `in_strip_row` without the strip's shared tag.

    `alone` is `standalone` without a coil's contact table; `no_cells` and `nc_cells` are its
    two columns of cells.
    """

    standalone: Extent
    in_strip_row: Extent
    alone: Extent
    no_cells: tuple[str, ...] = ()
    nc_cells: tuple[str, ...] = ()
