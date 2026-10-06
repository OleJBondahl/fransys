"""Vocabulary: typed accessors over `Model.tables` (kernel-model.md 5.5 and derive.md).

`kernel.Model.tables` stays generic (`kind -> id -> record`); every function here is a
thin, typed view over one kind, so callers never spell a kind string. Each returns the
model's own table, so nothing is copied, and an empty table when the model holds none of
that kind.
"""

from typing import Any, cast

from fransys_model.kernel import Id, Model, Record, SchemaError, namespace_of

from .aspects import AspectNode, Placement
from .connectivity import Conductor, Mate, Net
from .core import Function, Item, Port, Unit, UnitRelease
from .document import Document
from .project import Project
from .revision import Revision
from .supply_system import SupplySystem
from .templates import FunctionTemplate, InternalLink, Part, PartLibrary, PortTemplate
from .units import Boundary, UnusedBoundary

_NO_RECORDS: frozendict[Id[Any], Any] = frozendict()


def kind_of(record_type: type) -> str:
    """The kind `record_type` is registered under.

    Raises `SchemaError` when `record_type` is not a `@record` class.
    """
    # The two isinstance tests stay: a non-class argument is tested and must raise SchemaError.
    kind = (
        vars(record_type).get("__kind__")
        if isinstance(record_type, type)  # ty: ignore[redundant-condition-strict] -- see above
        else None
    )
    if kind is None:
        name = (
            record_type.__qualname__
            if isinstance(record_type, type)  # ty: ignore[redundant-condition-strict] -- see above
            else repr(record_type)
        )
        msg = f"{name} is not a @record class"
        raise SchemaError(msg, kind=name)
    return cast("str", kind)  # vars() values are Any; `@record` sets `__kind__` to a str


def table_of[R](model: Model, record_type: type[R]) -> frozendict[Id[R], R]:
    """The model's table of `record_type`, or an empty one."""
    return cast("frozendict[Id[R], R]", model.tables.get(kind_of(record_type), _NO_RECORDS))


def parts(model: Model) -> frozendict[Id[Part], Part]:
    """Return every `Part` in `model`, by id."""
    return table_of(model, Part)


def part_libraries(model: Model) -> frozendict[Id[PartLibrary], PartLibrary]:
    """Return every `PartLibrary` in `model`, by id."""
    return table_of(model, PartLibrary)


def function_templates(model: Model) -> frozendict[Id[FunctionTemplate], FunctionTemplate]:
    """Return every `FunctionTemplate` in `model`, by id."""
    return table_of(model, FunctionTemplate)


def port_templates(model: Model) -> frozendict[Id[PortTemplate], PortTemplate]:
    """Return every `PortTemplate` in `model`, by id."""
    return table_of(model, PortTemplate)


def internal_links(model: Model) -> frozendict[Id[InternalLink], InternalLink]:
    """Return every `InternalLink` in `model`, by id."""
    return table_of(model, InternalLink)


def items(model: Model) -> frozendict[Id[Item], Item]:
    """Return every `Item` in `model`, by id.

    Args:
        model: The model to read.

    Returns:
        Every `Item` in `model`, keyed by id; the model's own table, so nothing is
        copied. Empty when the model holds none.
    """
    return table_of(model, Item)


def functions(model: Model) -> frozendict[Id[Function], Function]:
    """Return every `Function` in `model`, by id.

    Args:
        model: The model to read.

    Returns:
        Every `Function` in `model`, keyed by id; the model's own table, so nothing is
        copied. Empty when the model holds none.
    """
    return table_of(model, Function)


def ports(model: Model) -> frozendict[Id[Port], Port]:
    """Return every `Port` in `model`, by id.

    Args:
        model: The model to read.

    Returns:
        Every `Port` in `model`, keyed by id; the model's own table, so nothing is
        copied. Empty when the model holds none.
    """
    return table_of(model, Port)


def nets(model: Model) -> frozendict[Id[Net], Net]:
    """Return every `Net` in `model`, by id.

    Args:
        model: The model to read.

    Returns:
        Every `Net` in `model`, keyed by id; the model's own table, so nothing is
        copied. Empty when the model holds none.
    """
    return table_of(model, Net)


def conductors(model: Model) -> frozendict[Id[Conductor], Conductor]:
    """Return every `Conductor` in `model`, by id.

    Args:
        model: The model to read.

    Returns:
        Every `Conductor` in `model`, keyed by id; the model's own table, so nothing is
        copied. Empty when the model holds none.
    """
    return table_of(model, Conductor)


def mates(model: Model) -> frozendict[Id[Mate], Mate]:
    """Return every `Mate` in `model`, by id."""
    return table_of(model, Mate)


def units(model: Model) -> frozendict[Id[Unit], Unit]:
    """Return every `Unit` in `model`, by id.

    Args:
        model: The model to read.

    Returns:
        Every `Unit` in `model`, keyed by id; the model's own table, so nothing is
        copied. Empty when the model holds none.
    """
    return table_of(model, Unit)


def unit_releases(model: Model) -> frozendict[Id[UnitRelease], UnitRelease]:
    """Return every `UnitRelease` in `model`, by id.

    Args:
        model: The model to read.

    Returns:
        Every `UnitRelease` in `model`, keyed by id; the model's own table, so nothing is
        copied. Empty when the model holds none.
    """
    return table_of(model, UnitRelease)


def boundaries(model: Model) -> frozendict[Id[Boundary], Boundary]:
    """Return every `Boundary` in `model`, by id.

    Args:
        model: The model to read.

    Returns:
        Every `Boundary` in `model`, keyed by id; the model's own table, so nothing is
        copied. Empty when the model holds none.
    """
    return table_of(model, Boundary)


def supply_systems(model: Model) -> frozendict[Id[SupplySystem], SupplySystem]:
    """Return every `SupplySystem` in `model`, by id.

    Args:
        model: The model to read.

    Returns:
        Every `SupplySystem` in `model`, keyed by id; the model's own table, so nothing
        is copied. Empty when the model holds none.
    """
    return table_of(model, SupplySystem)


def supply_of_potential(model: Model, potential: str) -> SupplySystem | None:
    """The supply declaring `potential` as a rail (smallest `(name, id)` if two), else `None`."""
    declaring = [supply for supply in supply_systems(model).values() if potential in supply.rails]
    return min(declaring, key=lambda supply: (supply.name, supply.id)) if declaring else None


def unused_boundaries(model: Model) -> frozendict[Id[UnusedBoundary], UnusedBoundary]:
    """Return every `UnusedBoundary` in `model`, by id."""
    return table_of(model, UnusedBoundary)


def aspect_nodes(model: Model) -> frozendict[Id[AspectNode], AspectNode]:
    """Return every `AspectNode` in `model`, by id.

    Args:
        model: The model to read.

    Returns:
        Every `AspectNode` in `model`, keyed by id; the model's own table, so nothing is
        copied. Empty when the model holds none.
    """
    return table_of(model, AspectNode)


def placements(model: Model) -> frozendict[Id[Placement], Placement]:
    """Return every `Placement` in `model`, by id.

    Args:
        model: The model to read.

    Returns:
        Every `Placement` in `model`, keyed by id; the model's own table, so nothing is
        copied. Empty when the model holds none.
    """
    return table_of(model, Placement)


def documents(model: Model) -> frozendict[Id[Document], Document]:
    """Return every `Document` in `model`, by id."""
    return table_of(model, Document)


def projects(model: Model) -> frozendict[Id[Project], Project]:
    """Return the `Project` in `model`, by id; empty or one entry (`Project` is a singleton)."""
    return table_of(model, Project)


def revisions(model: Model) -> frozendict[Id[Revision], Revision]:
    """Return every `Revision` in `model`, by id."""
    return table_of(model, Revision)


def facets_of[F](model: Model, facet_type: type[F]) -> frozendict[Id[F], F]:
    """Return every facet of `facet_type` in `model`, keyed by the facet's own id.

    Not by its `subject`: a subject may carry several facets of different kinds, and
    `supply` allows several of the same kind (design/facets.md).

    Raises:
        SchemaError: `facet_type` is not a `@record` class of the `facet` namespace.
    """
    kind = kind_of(facet_type)
    if namespace_of(kind) != "facet":
        msg = f"{facet_type.__qualname__} is not a facet: kind {kind} is not in the facet namespace"
        raise SchemaError(msg, kind=kind)
    return table_of(model, facet_type)


def facet_subject(facet: Record) -> Id[Any]:
    """Return the id `facet` describes: the value of the field its kind declared as `subject`.

    Raises:
        SchemaError: `facet` is a record of a kind that declares no subject, so not a facet.
    """
    field = vars(type(facet)).get("__subject__")
    if field is None:
        msg = f"{type(facet).__qualname__} declares no subject, so it is not a facet"
        raise SchemaError(msg, kind=facet.id.kind, record_id=facet.id)
    return getattr(facet, field)
