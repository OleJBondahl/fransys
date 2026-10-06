"""Invented connectors for the `connector_rows` tests: a connector function with its facet."""

from typing import TYPE_CHECKING

from query_builders import make_part

from fransys_model.kernel import Id, make_id
from fransys_model.vocab.core import Function, Item, Port
from fransys_model.vocab.enums import FunctionKind, Gender
from fransys_model.vocab.facets.connector import ConnectorFacet
from fransys_model.vocab.templates import FunctionTemplate

if TYPE_CHECKING:
    from plant import Plant


def make_connector(  # noqa: PLR0913 -- one keyword per facet field the tests vary
    plant: Plant,
    key: tuple[str, str],
    markings: tuple[str, ...],
    *,
    gender: Gender | None = Gender.MALE,
    kind: FunctionKind = FunctionKind.CONNECTOR,
    marking: str | None = None,
) -> tuple[Id[Function], dict[str, Id[Port]]]:
    """The function `key` = (item key, function name), with a port per marking.

    The item must be added by the caller. The function has a template that carries a
    `connector` facet of this `gender` and `marking`, or none when `gender` is `None`.
    """
    item_key, name = key
    part = make_part(plant, f"cp-{item_key}-{name}", f"CP-{item_key}-{name}")
    template = FunctionTemplate(
        id=make_id(FunctionTemplate, (item_key, name, "template")),
        key=(item_key, name, "template"),
        part=part,
        name=name,
        kind=kind,
    )
    function = Function(
        id=make_id(Function, (item_key, name)),
        key=(item_key, name),
        item=make_id(Item, (item_key,)),
        template=template.id,
        name=name,
        kind=kind,
    )
    plant.add(template, function)
    if gender is not None:
        plant.add(
            ConnectorFacet(
                id=make_id(ConnectorFacet, (item_key, name, "connector")),
                key=(item_key, name, "connector"),
                subject=template.id,
                style="header",
                pincount=len(markings),
                gender=gender,
                marking=marking,
            )
        )
    return function.id, {marking: plant.port(function.id, marking) for marking in markings}
