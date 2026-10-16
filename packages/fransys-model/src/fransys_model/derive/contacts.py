"""Changeover throws and link states re-exported from `facts.contacts`, and `owned_contacts`.

Decision 0019 (CONTACT-STATES CS2). `owned_contacts` is the one answer to "which contacts does a
designation holder own" (model-0119).
"""

from types import MappingProxyType
from typing import TYPE_CHECKING

from fransys_model.derive.designation import designation_holder
from fransys_model.derive.facts.contacts import (
    LinkState,
    Throws,
    changeover_throws,
    link_state,
    link_throw,
)
from fransys_model.derive.indexes import build_indexes
from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, digest_cached
lazy from fransys_model.derive.facts.roles import function_role
lazy from fransys_model.vocab.core import Function, Item

if TYPE_CHECKING:
    from collections.abc import Mapping


@digest_cached(DIGEST_CACHE_SIZE)
def _contacts_by_device(model: Model) -> Mapping[Id[Item], tuple[Id[Function], ...]]:
    """Each contact function, grouped under the item whose designation its item prints."""
    found: dict[Id[Item], list[Id[Function]]] = {}
    for item, own in build_indexes(model).functions_by_item.items():
        mine = [f for f in own if function_role(model, f).plain_contact]
        if mine:
            found.setdefault(designation_holder(model, item), []).extend(mine)
    return MappingProxyType({item: tuple(sorted(ids)) for item, ids in found.items()})


def owned_contacts(model: Model, device: Id[Item]) -> tuple[Id[Function], ...]:
    """The contact functions `device` owns, sorted by id: its own and its add-on blocks'.

    An add-on block prints `device`'s designation, so its contacts are the
    device's. Layout's contact table and the contacts' home references read it.
    """
    return _contacts_by_device(model).get(device, ())


__all__ = [
    "LinkState",
    "Throws",
    "changeover_throws",
    "link_state",
    "link_throw",
    "owned_contacts",
]
