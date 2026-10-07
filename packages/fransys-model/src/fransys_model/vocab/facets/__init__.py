"""Domain facets: typed, per-subject facts layered onto a `Part`/`Item`/`Function`/etc.

design/facets.md. Adding a domain means adding a module here, never touching `core.py` or
`derive.closure`.
"""

from .assigned_designation import AssignedDesignationFacet
from .assigned_unit_tag import AssignedUnitTagFacet
from .cable import CableFacet, CableProductFacet, CoreFacet
from .connector import ConnectorFacet
from .crimp import ContactFit, ContactsFacet
from .harness import HarnessFacet
from .pcb import FootprintFacet, PcbFacet
from .plc import PlcBindingFacet, PlcChannelFacet, PlcRequestFacet
from .rating import BoundaryValuesFacet, OperatingFacet, PartRatingFacet, RatingFacet
from .reserved_designation import ReservedDesignationFacet
from .scaling import ScalingFacet
from .supply import SupplyFacet
from .terminal import TerminalFacet
from .wire import WireFacet

__all__ = [
    "AssignedDesignationFacet",
    "AssignedUnitTagFacet",
    "BoundaryValuesFacet",
    "CableFacet",
    "CableProductFacet",
    "ConnectorFacet",
    "ContactFit",
    "ContactsFacet",
    "CoreFacet",
    "FootprintFacet",
    "HarnessFacet",
    "OperatingFacet",
    "PartRatingFacet",
    "PcbFacet",
    "PlcBindingFacet",
    "PlcChannelFacet",
    "PlcRequestFacet",
    "RatingFacet",
    "ReservedDesignationFacet",
    "ScalingFacet",
    "SupplyFacet",
    "TerminalFacet",
    "WireFacet",
]
