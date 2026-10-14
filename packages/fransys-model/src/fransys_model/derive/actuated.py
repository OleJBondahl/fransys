"""The switches one actuator moves, and the lead among them (model-0237, ACTUATOR-ONCE AO1, AO2).

A group is the `switch` functions whose operator one item states; the lead is the one that
draws the actuator, the first of the group's contact list that is wired.
"""

from collections import defaultdict

from fransys_model.derive.accessory_blocks import operating_item
from fransys_model.derive.contact_entries import contact_list_key
from fransys_model.derive.unused import function_is_unused
from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, digest_cached
from fransys_model.layout import profile_of
from fransys_model.vocab.enums import FunctionKind
from fransys_model.vocab.tables import functions
lazy from fransys_model.vocab.core import Function, Item, Unit


@digest_cached(DIGEST_CACHE_SIZE)
def _groups(model: Model) -> dict[Id[Item], tuple[Id[Function], ...]]:
    """Each operating item's switch functions in contact-list order."""
    found: dict[Id[Item], list[Id[Function]]] = defaultdict(list)
    for function, record in functions(model).items():
        if record.kind is FunctionKind.SWITCH and (item := operating_item(model, function)):
            found[item].append(function)
    return {
        item: tuple(sorted(group, key=lambda f: (contact_list_key(model, f), f)))
        for item, group in found.items()
    }


def actuated_group(model: Model, function: Id[Function]) -> tuple[Id[Function], ...]:
    """The switches the actuator of `function` moves, in list order; empty with no operator."""
    item = operating_item(model, function)
    return () if item is None else _groups(model)[item]


def lead_switch(model: Model, function: Id[Function]) -> Id[Function] | None:
    """The first switch of `function`'s group that is wired, else the group's first; else None."""
    group = actuated_group(model, function)
    return next((f for f in group if not function_is_unused(model, f)), group[0] if group else None)


def actuator_each_contact(model: Model, unit: Id[Unit] | None) -> bool:
    """Whether `unit`'s profile draws the actuator on every contact (the default)."""
    return profile_of(model, unit).actuator_each_contact
