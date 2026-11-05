"""Stage 6a: the fixed wires that read the placement alone, the trunks (R872, layout-0453).

They are laid right after placement, before the markers stand, so a marker yields to them and no
fixed wire ever moves for a marker (R535 R-B). Routed wires come after the markers (stage 6b).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

from .route_env import Drawn, LostKey, route_envs, withheld
from .route_trunk import trunk_wires

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .annex_values import AnnexBox
    from .clearance import Keep
    from .flow_values import CutResult
    from .outputs import Marker, Placement
    from .route_env import RouteEnv
    from .values import Options, PlacementProblem


class Fixed(NamedTuple):
    """One page's trunk wires (with their drops), and the labels the round before stood on it: they do not move (TEXT-CANDIDATES)."""

    trunks: Drawn
    labels: tuple[AnnexBox, ...] = ()


class Laid(NamedTuple):
    """What stands before the A* round: the marker and anchor keeps, and the trunk wires (none given: laid at routing)."""

    keeps: Sequence[Keep] = ()
    fixed: Mapping[int, Fixed] | None = None
    lost: frozenset[LostKey] = frozenset[LostKey]()
    markers: Sequence[Marker] = ()


def fixed_page(env: RouteEnv) -> Fixed:
    """The trunks of one page, in their order."""
    trunks = Drawn()
    for trunk in env.trunks:
        trunks += trunk_wires(env, trunk)
    return Fixed(trunks)


def fixed_wires(
    placement: Placement, cut: CutResult, problem: PlacementProblem, options: Options, *, lost: frozenset[LostKey] = frozenset[LostKey]()
) -> dict[int, Fixed]:
    """The fixed wires of every placed page, by page number; a `lost` conductor is withheld."""
    return {env.page: fixed_page(env) for env in withheld(route_envs(placement, cut, problem, options), lost)}
