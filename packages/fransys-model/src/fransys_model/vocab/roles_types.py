"""The role value types and the completeness check of the role tables (EL-2a, model-0288).

A role is a table row: a frozen value keyed by an enum member. A table is data; the readers that
refine a row by the model's facets live in `derive/facts/roles.py`, and nothing else reads a kind.
"""

from enum import Enum
lazy from collections.abc import Mapping

from fransys_model.kernel import ModelError, value

from .enums import Energy


@value
class FunctionRole:
    """What a `FunctionKind` is for; each field reproduces one kind branch (comment on its row).

    Example: `function_role_of(FunctionKind.CONTACT_NO)` has `contact` and `closed_at_rest=False`.
    `plain_contact` leaves out `SWITCH`.
    """

    contact: bool = False
    plain_contact: bool = False
    closed_at_rest: bool | None = None
    changeover: bool = False
    operator: bool = False
    terminal: bool = False
    pin_group: bool = False
    channel: bool = False
    # protects: an overcurrent protective device: it carries a protection rating and clears faults
    protects: bool = False
    through: bool = False
    energy: Energy | None = None
    box: bool = False
    band: str | None = None


@value
class LinkRole:
    """What a `LinkKind` does: `pole` for a switched or protective link, `joins_net` if physical.

    `passes_rail` is true if a supply rail spreads across the link (the closure's rail pass).
    `closed_at_rest` is the link's state at rest; the table leaves it `None` because a link declares it.
    """

    pole: bool = False
    joins_net: bool = False
    switched: bool = False
    protective: bool = False
    passes_rail: bool = False
    closed_at_rest: bool | None = None


def complete[K: Enum, R](table: Mapping[K, R], enum_cls: type[K]) -> Mapping[K, R]:
    """Return `table` if it has a row for every member of `enum_cls`, else raise `ModelError`.

    The error names the enum and each missing member, so a kind added without a row fails import.
    """
    missing = [member.name for member in enum_cls if member not in table]
    if missing:
        msg = f"{enum_cls.__name__} has no role row for: {', '.join(missing)}"
        raise ModelError(msg)
    return table


@value
class ItemRole:
    """What an `ItemKind` is, plus the facet-read flags the table leaves false.

    Example: `ITEM_ROLES[ItemKind.STRIP]` has `strip`; a strip's terminal has `terminal`.
    `rack`, `external` and `unit_root` come from facets: every row leaves them false.
    """

    strip: bool = False
    terminal: bool = False
    board: bool = False
    cable: bool = False
    harness: bool = False
    rack: bool = False
    external: bool = False
    unit_root: bool = False


@value
class ConductorRole:
    """What a `ConductorKind` is: a wire that `carries`, or a link that `joins_net`.

    Example: `CONDUCTOR_ROLES[ConductorKind.JUMPER]` has `bridge` and `joins_net`.
    `lands` adds `LEAD` to what `carries`: a device's own lead lands a line but is not a wire.
    """

    wire: bool = False
    carries: bool = False
    lands: bool = False
    joins_net: bool = False
    bridge: bool = False
    mount: bool = False
    lead: bool = False


@value
class NetClassRole:
    """What a `NetClass` is for the drawing: a signal or earth."""

    signal: bool = False
    earth: bool = False
