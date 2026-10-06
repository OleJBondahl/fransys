"""Changeover throws and link states re-exported from `vocab.contacts`, and `owned_contacts`.

Decision 0019 (CONTACT-STATES CS2). The throws and states live in `vocab` because `vocab.closure`
reads them and `vocab` never imports `derive`. `owned_contacts` is the one answer to "which
contacts does a designation holder own" (model-0119).
"""

from types import MappingProxyType
from typing import TYPE_CHECKING

from fransys_model.derive.accessory_blocks import CONTACT_KINDS
from fransys_model.derive.designation import designation_holder
from fransys_model.derive.indexes import build_indexes
from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, digest_cached
from fransys_model.vocab.contacts import LinkState, Throws, changeover_throws, link_state
from fransys_model.vocab.tables import functions
lazy from fransys_model.vocab.core import Function, Item

if TYPE_CHECKING:
    from collections.abc import Mapping


@digest_cached(DIGEST_CACHE_SIZE)
def _contacts_by_device(model: Model) -> Mapping[Id[Item], tuple[Id[Function], ...]]:
    """Each contact function, grouped under the item whose designation its item prints."""
    known = functions(model)
    found: dict[Id[Item], list[Id[Function]]] = {}
    for item, own in build_indexes(model).functions_by_item.items():
        mine = [f for f in own if known[f].kind in CONTACT_KINDS]
        if mine:
            found.setdefault(designation_holder(model, item), []).extend(mine)
    return MappingProxyType({item: tuple(sorted(ids)) for item, ids in found.items()})


def owned_contacts(model: Model, device: Id[Item]) -> tuple[Id[Function], ...]:
    """The contact functions `device` owns, sorted by id: its own and its add-on blocks'.

    An add-on block prints `device`'s designation, so its contacts are the
    device's. Layout's contact table and the contacts' home references read it.
    """
    return _contacts_by_device(model).get(device, ())


__all__ = ["LinkState", "Throws", "changeover_throws", "link_state", "owned_contacts"]
