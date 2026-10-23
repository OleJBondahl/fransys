"""The cable list: one row per core of a cable, with its colour and both ends.

A core's colour is the cable product's fact (`derive.facts.cores`); a core past its product
prints "" (decision 0021).
"""

from typing import TYPE_CHECKING

from fransys_model.derive.facts.cores import core_colour_at
from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, SchemaError, digest_cached
from fransys_model.vocab.enums import ConductorKind
from fransys_model.vocab.facets.cable import CoreFacet
from fransys_model.vocab.tables import conductors, facets_of, items
lazy from fransys_model.vocab.connectivity import Conductor
lazy from fransys_model.vocab.core import Item, Unit
lazy from fransys_model.vocab.facets.cable import CableProductFacet

from .cable_end_rank import cable_end_owner, cable_end_rank
from .core_pairs import cable_product
from .designation import port_designation, printed_designation, unit_list_context
from .lookups import item_of_port, require
from .report_scope import _require_unit
from .rows import CableRow
from .texts.context import PrintContext
from .texts.end_text import FAR_END, end_text

if TYPE_CHECKING:
    from fransys_model.vocab.core import Port


@digest_cached(DIGEST_CACHE_SIZE)
def _cores_by_cable(model: Model) -> frozendict[Id[Item], tuple[tuple[Conductor, CoreFacet], ...]]:
    """Every core conductor and its `CoreFacet`, grouped by the cable (`carrier`) it belongs to.

    Built once per model digest from `ConductorKind.CORE` conductors with a carrier and facet.
    """
    core_of = {facet.subject: facet for facet in facets_of(model, CoreFacet).values()}
    grouped: dict[Id[Item], list[tuple[Conductor, CoreFacet]]] = {}
    for conductor in conductors(model).values():
        facet = core_of.get(conductor.id)
        if conductor.kind is not ConductorKind.CORE or conductor.carrier is None or facet is None:
            continue
        grouped.setdefault(conductor.carrier, []).append((conductor, facet))
    return frozendict({cable: tuple(pairs) for cable, pairs in grouped.items()})


def _oriented_ends(model: Model, a: Id[Port], b: Id[Port]) -> tuple[Id[Port], Id[Port]]:
    """`(a, b)`, swapped if needed so the first port's end outranks the second's.

    A `Conductor`'s `a`/`b` are in port-id order, so a core's physical direction is derived here.
    Shared by `cable_rows` and `derive.harness`, so every output agrees on which end is first.
    """
    rank_a = cable_end_rank(model, cable_end_owner(model, item_of_port(model, a)))
    rank_b = cable_end_rank(model, cable_end_owner(model, item_of_port(model, b)))
    return (a, b) if rank_a <= rank_b else (b, a)


def _colour_of(product: CableProductFacet | None, index: int) -> str:
    """The colour of core `index` of `product`; "" for no product or an index past it."""
    return "" if product is None else core_colour_at(product, index) or ""


def core_colour(model: Model, conductor: Id[Conductor]) -> str:
    """The colour of core `conductor`: its carrier's `core_colours[index - 1]`.

    The one reader of a core's colour: the facet holds only the index, and the colour is the cable
    product's fact. `cable_rows`, the harness rows and wireviz read it here.

    Args:
        model: The frozen model to read.
        conductor: The core conductor whose colour to render.

    Returns:
        The core's colour, an IEC 60757 code (or code pair); "" for a core past its product.

    Raises:
        SchemaError: `conductor` is not a core of a cable, or has no `core` facet.
    """
    record = require(conductors(model).get(conductor), "conductor", conductor)
    if record.kind is not ConductorKind.CORE or record.carrier is None:
        msg = "a conductor that is not a cable core has no core colour"
        raise SchemaError(msg, kind="conductor", record_id=conductor)
    for facet in facets_of(model, CoreFacet).values():
        if facet.subject == conductor:
            return _colour_of(cable_product(model, record.carrier), facet.index)
    msg = "a core with no `core` facet has no index, so no colour"
    raise SchemaError(msg, kind="conductor", record_id=conductor)


def cable_rows(
    model: Model, cable: Id[Item], *, unit: Id[Unit] | None = None
) -> tuple[CableRow, ...]:
    """One `CableRow` per core of `cable`, sorted by `(core.index, conductor id)`.

    Cores are the `core`-kind conductors naming `cable` as `carrier`; the colour is `core_colour`'s.

    Args:
        model: The frozen model to read.
        cable: The cable item whose cores to list.
        unit: The unit whose own document draws the cable, keyword-only; `None` is the whole model.

    Returns:
        One `CableRow` per core of `cable`, sorted.

    Raises:
        SchemaError: `cable` is no item, an end has no designation, or `unit` is no unit of `model`.
    """
    require(items(model).get(cable), "item", cable)
    _require_unit(model, unit)
    context = unit_list_context(model, unit, None)

    def cable_end(port: Id[Port]) -> str:
        if unit is None:
            return port_designation(model, port)
        return end_text(model, port, FAR_END, PrintContext(reading=unit, location=context))

    product = cable_product(model, cable)
    rows = []
    for conductor, facet in _cores_by_cable(model).get(cable, ()):
        end_a, end_b = _oriented_ends(model, conductor.a, conductor.b)
        rows.append(
            CableRow(
                cable=cable,
                cable_designation=printed_designation(model, cable, unit=unit),
                index=facet.index,
                colour=_colour_of(product, facet.index),
                conductor=conductor.id,
                end_a=end_a,
                end_a_designation=cable_end(end_a),
                end_b=end_b,
                end_b_designation=cable_end(end_b),
            )
        )
    return tuple(sorted(rows, key=lambda row: (row.index, row.conductor)))
