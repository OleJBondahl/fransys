"""Finding messages name a thing as the drawings print it, never by key or Id (overview-0003).

A validator in `vocab` writes `ref(...)` (`vocab.finding_ref`); `name_findings` replaces each
reference with `name_of`, the one text of a thing in a message. A thing with no printed text is
named by its kind alone.
"""

import dataclasses
from typing import TYPE_CHECKING, Any

from fransys_model.derive.designation import (
    can_print_designation,
    port_designation,
    printed_designation,
)
from fransys_model.derive.drawing_text import outline_title, tag_text, wire_text
from fransys_model.derive.instance_tag import instance_name, unit_tag
from fransys_model.derive.kinds import item_kind
from fransys_model.derive.plc_channel_text import plc_channel_text
from fransys_model.kernel import Finding, Id, Model, Record, SchemaError
from fransys_model.vocab.finding_ref import REF
from fransys_model.vocab.tables import conductors, nets
from fransys_model.vocab.tables import units as units_table

if TYPE_CHECKING:
    import re
    from collections.abc import Callable


__all__ = ["name_findings", "name_of"]


def _item(model: Model, target: Id[Any]) -> str:
    if can_print_designation(model, target):
        return printed_designation(model, target)
    return item_kind(model, target).value.replace("_", " ")


def _unit(model: Model, target: Id[Any]) -> str:
    if target not in units_table(model):
        return "unit"
    tag = unit_tag(model, target)
    return outline_title(model, target) if tag is None else f"unit {instance_name((tag,))}"


def _net(model: Model, target: Id[Any]) -> str:
    return (nets(model)[target].name or "net") if target in nets(model) else "net"


def _wire(model: Model, target: Id[Any]) -> str:
    try:
        return wire_text(model, target)
    except SchemaError:  # an end that prints no designation
        return conductors(model)[target].kind.value


def _port(model: Model, target: Id[Any]) -> str:
    try:
        return port_designation(model, target)
    except SchemaError:
        return "port"


def _function(model: Model, target: Id[Any]) -> str:
    try:
        if (channel := plc_channel_text(model, target)) is not None:
            return channel
        return tag_text(model, target)
    except SchemaError:
        return "function"


_NAMERS: dict[str, Callable[[Model, Id[Any]], str]] = {
    "item": _item,
    "port": _port,
    "conductor": _wire,
    "function": _function,
    "unit": _unit,
    "net": _net,
}


def name_of(model: Model, target: Id[Record]) -> str:
    """`target` as the drawings print it: its designation, its ends or its tag; else its kind."""
    namer = _NAMERS.get(target.kind)
    return target.kind if namer is None else namer(model, target)


def _replace(model: Model, match: re.Match[str]) -> str:
    return name_of(model, Id(kind=match.group(1), value=match.group(2)))


def name_findings(model: Model, findings: tuple[Finding, ...]) -> tuple[Finding, ...]:
    """Each finding with every reference in its message printed as `name_of`."""
    return tuple(
        dataclasses.replace(finding, message=REF.sub(lambda m: _replace(model, m), finding.message))
        for finding in findings
    )
