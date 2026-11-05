"""Domain layer: record kinds, facets, built on kernel."""

from fransys_model.kernel import register_namespaces, register_schema_version

from .aspects import AspectNode, Placement
from .codes import FINDING_CODES
from .colours import BASE_COLOURS, COLOUR_GRAMMAR, RESERVED_CODES
from .conductor_marks import CONDUCTOR_MARKS
from .connectivity import Conductor, Mate, Net, RailGroup
from .core import Function, Item, Port, Unit, UnitRelease
from .designation_scheme import DESIGNATION_SCHEME
from .document import Document
from .enums import (
    Aspect,
    ConductorKind,
    ConductorMark,
    DocumentPreset,
    Energy,
    FunctionKind,
    NetClass,
    OperatedBy,
    PageKind,
    PartCategory,
    PortBoundary,
    PowerKind,
    ProtectionType,
    SignalType,
    SubjectKind,
)
from .facets import (
    AssignedDesignationFacet,
    AssignedUnitTagFacet,
    BlockFacet,
    CableFacet,
    CableProductFacet,
    ConnectorFacet,
    ContactFit,
    ContactsFacet,
    CoreFacet,
    CorePair,
    FootprintFacet,
    HarnessFacet,
    OpenCoreFacet,
    OperatingFacet,
    PartRatingFacet,
    PcbFacet,
    PlcBindingFacet,
    PlcChannelFacet,
    PlcRequestFacet,
    RatingFacet,
    ReservedDesignationFacet,
    RowSpec,
    ScalingFacet,
    SupplyFacet,
    TerminalFacet,
    WireFacet,
    WireRowHint,
)
from .finding_ref import ref
from .instantiate import PartBundle
from .markings import (
    Pole,
    identifier,
)
from .operating import Operating
from .project import Project
from .rail_defaults import RAIL_DEFAULTS
from .revision import Revision
from .schema_version import SCHEMA_VERSION
from .supply_system import Rail, SupplySystem, supply_rail_row
from .tables import (
    Boundary,
    UnusedBoundary,
    UnusedPort,
    aspect_nodes,
    boundaries,
    conductors,
    facet_subject,
    facets_of,
    functions,
    items,
    nets,
    part_libraries,
    parts,
    placements,
    ports,
    projects,
    revisions,
    supply_systems,
    unit_releases,
    units,
)
from .templates import FunctionTemplate, InternalLink, Part, PartLibrary, PortTemplate
from .wiring_rows import WiringRow

# The kernel knows only `core`; the layers above name the rest, once, in this order. A
# reference may point at the same namespace or an earlier one (decision 0009).
register_namespaces("facet", "layout")
# The schema version is the electrical schema's: it moves with a vocab or layout kind, and the
# kernel stamps and checks the number registered here (model-0251).
register_schema_version(SCHEMA_VERSION)

__all__ = [
    "BASE_COLOURS",
    "COLOUR_GRAMMAR",
    "CONDUCTOR_MARKS",
    "DESIGNATION_SCHEME",
    "FINDING_CODES",
    "RAIL_DEFAULTS",
    "RESERVED_CODES",
    "SCHEMA_VERSION",
    "Aspect",
    "AspectNode",
    "AssignedDesignationFacet",
    "AssignedUnitTagFacet",
    "BlockFacet",
    "Boundary",
    "CableFacet",
    "CableProductFacet",
    "Conductor",
    "ConductorKind",
    "ConductorMark",
    "ConnectorFacet",
    "ContactFit",
    "ContactsFacet",
    "CoreFacet",
    "CorePair",
    "Document",
    "DocumentPreset",
    "Energy",
    "FootprintFacet",
    "Function",
    "FunctionKind",
    "FunctionTemplate",
    "HarnessFacet",
    "InternalLink",
    "Item",
    "Mate",
    "Net",
    "NetClass",
    "OpenCoreFacet",
    "OperatedBy",
    "Operating",
    "OperatingFacet",
    "PageKind",
    "Part",
    "PartBundle",
    "PartCategory",
    "PartLibrary",
    "PartRatingFacet",
    "PcbFacet",
    "Placement",
    "PlcBindingFacet",
    "PlcChannelFacet",
    "PlcRequestFacet",
    "Pole",
    "Port",
    "PortBoundary",
    "PortTemplate",
    "PowerKind",
    "Project",
    "ProtectionType",
    "Rail",
    "RailGroup",
    "RatingFacet",
    "ReservedDesignationFacet",
    "Revision",
    "RowSpec",
    "ScalingFacet",
    "SignalType",
    "SubjectKind",
    "SupplyFacet",
    "SupplySystem",
    "TerminalFacet",
    "Unit",
    "UnitRelease",
    "UnusedBoundary",
    "UnusedPort",
    "WireFacet",
    "WireRowHint",
    "WiringRow",
    "aspect_nodes",
    "boundaries",
    "conductors",
    "facet_subject",
    "facets_of",
    "functions",
    "identifier",
    "items",
    "nets",
    "part_libraries",
    "parts",
    "placements",
    "ports",
    "projects",
    "ref",
    "revisions",
    "supply_rail_row",
    "supply_systems",
    "unit_releases",
    "units",
]
