"""The pole side and conductor of a port: the stated value, else the one a standard marking gives.

Decision parts-0010. The rules are `fransys_model.derive.pole_side` and `conductor_of`; this
module only reads the pole pins off the raw entry, which has no templates yet.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from fransys_model.derive import conductor_of, pole_pin_names, pole_side
from fransys_model.vocab import FunctionKind, LinkKind

if TYPE_CHECKING:
    from fransys_model.vocab import PortTemplate

    from . import _toml


def pole_ports(entry: _toml.Table) -> set[str]:
    """The names of the ports on a switched or protective link of this function."""
    links = (
        (link["a"], link["b"], LinkKind(link["kind"]))
        for link in entry.get("links", ())
        if "kind" in link
    )
    return set(pole_pin_names(FunctionKind(entry["kind"]), links))


def with_facts(template: PortTemplate, entry: _toml.Table, pole_pins: set[str]) -> PortTemplate:
    """The template with its side and conductor filled in; a stated one wins."""
    side = pole_side(template, FunctionKind(entry["kind"]), pole_pins)
    return replace(template, pole_side=side, conductor_mark=conductor_of(template))
