"""The lane each jumper group's row span takes in the terminal list's Bridge column (pdf-0007)."""

from dataclasses import dataclass

from fransys_model.kernel import value


@value
class JumperLane:
    """One jumper group's row span and its lane; `first` and `last` are 0-based row indexes."""

    group: int
    first: int
    last: int
    lane: int


@value
class JumperLanes:
    """Every jumper group's lane, in group-number order."""

    lanes: tuple[JumperLane, ...]


@dataclass(frozen=True)  # plain: the closed value set bans float
class BridgePiece:
    """One drawn Bridge mark piece (`bridge_piece_key`): its SVG and its size in mm.

    The SVG is `width_mm` by `height_mm`; pdf places it in a row's cell and, for a lane's `line`
    only, stretches it on y to the rows the lane covers.
    """

    svg: str
    width_mm: float
    height_mm: float
