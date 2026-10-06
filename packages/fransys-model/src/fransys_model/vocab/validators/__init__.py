"""Domain validators: engineering checks that return `Finding`s, never raise (kernel-model.md)."""

from typing import TYPE_CHECKING

from .cables import check_cables
from .colours import check_colours
from .connectivity import check_connectivity
from .documents import check_documents
from .earth import check_earth
from .harness_without_tag import check_harness_without_tag
from .part_conformance import check_part_conformance
from .part_library import check_part_library
from .plc import check_plc, check_plc_wiring
from .potential_without_supply import check_potential_without_supply
from .ratings import check_ratings
from .ratings_current import check_ratings_current
from .revisions import check_revisions
from .strip_without_tag import check_strip_without_tag
from .structure import check_structure
from .supplies import check_supplies
from .units import check_units

if TYPE_CHECKING:
    from collections.abc import Callable

    from fransys_model.kernel import Finding, Model

ALL_VALIDATORS: tuple[Callable[[Model], tuple[Finding, ...]], ...] = (
    check_structure,
    check_part_conformance,
    check_part_library,
    check_connectivity,
    check_cables,
    check_colours,
    check_earth,
    check_harness_without_tag,
    check_strip_without_tag,
    check_plc,
    check_plc_wiring,
    check_units,
    check_supplies,
    check_ratings,
    check_ratings_current,
    check_revisions,
    check_documents,
    check_potential_without_supply,
)

__all__ = [
    "ALL_VALIDATORS",
    "check_cables",
    "check_colours",
    "check_connectivity",
    "check_documents",
    "check_earth",
    "check_harness_without_tag",
    "check_part_conformance",
    "check_part_library",
    "check_plc",
    "check_plc_wiring",
    "check_potential_without_supply",
    "check_ratings",
    "check_ratings_current",
    "check_revisions",
    "check_strip_without_tag",
    "check_structure",
    "check_supplies",
    "check_units",
]
