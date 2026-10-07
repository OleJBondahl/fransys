"""One read per interface of a unit: the facts HL13 splits its edges by (layout-0153)."""

from typing import TYPE_CHECKING

from fransys_layout.stages.edges import InterfaceEdge
from fransys_model.derive import connector_at_line_end, natural_key, supply_share
from fransys_model.derive.designation import connector_designation
from fransys_model.layout import Side, SideHint, layout_of
from fransys_model.vocab.membership import boundary
from fransys_model.vocab.tables import units

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Function, Unit


def _read(
    model: Model, f: Id[Function], parent: Id[Unit] | None, hint: Side | None
) -> InterfaceEdge:
    designation = connector_designation(model, f, unit=parent)
    return InterfaceEdge(
        function=f,
        designation=designation,
        order=natural_key(designation),
        hint=None if hint is None else hint is Side.N,
        line=connector_at_line_end(model, f),
        share=supply_share(model, f),
    )


def interface_reads(model: Model, unit: Id[Unit]) -> tuple[InterfaceEdge, ...]:
    """Each boundary function of `unit` with its hint, line fact and share; decides nothing."""
    hints = {h.function: h.side for h in layout_of(model, SideHint).values()}
    parent = units(model)[unit].parent
    return tuple(_read(model, f, parent, hints.get(f)) for f in boundary(model, unit))
