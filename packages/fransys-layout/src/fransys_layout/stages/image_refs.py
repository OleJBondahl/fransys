"""Contact images, V10: who owns a contact, and each contact's reference to its home."""

from typing import TYPE_CHECKING

from .types import LabelKind, LabelRequest, RequestPartner

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from .types import FunctionSpec, Handle, PlacedFunction


def by_owner(
    specs: Sequence[FunctionSpec], owners: Mapping[Handle, Handle] | None
) -> dict[Handle, list[FunctionSpec]]:
    """`specs` grouped under the item that owns each: the contact owner, else its own item."""
    found: dict[Handle, list[FunctionSpec]] = {}
    for spec in specs:
        found.setdefault((owners or {}).get(spec.function, spec.item), []).append(spec)
    return found


def unplaced_coil_owners(
    specs: Sequence[FunctionSpec],
    owners: Mapping[Handle, Handle] | None,
    home: Mapping[Handle, PlacedFunction],
) -> set[Handle]:
    """The owners whose coils are all unplaced: their contacts get no reference (V10)."""
    coils = {o: [s for s in g if s.roles.coil] for o, g in by_owner(specs, owners).items()}
    return {o for o, c in coils.items() if c and not any(s.function in home for s in c)}


def home_references(
    contacts: Sequence[FunctionSpec],
    main: FunctionSpec,
    home: Mapping[Handle, PlacedFunction],
    where: Callable[[PlacedFunction, PlacedFunction], str],
) -> list[LabelRequest]:
    """C19, V10: each contact's reference to `main` (its coil, else the device's main symbol)."""
    at = home[main.function]
    partner = RequestPartner(
        port=main.ports[0].port, drawing_set=at.drawing_set, page=at.page, x=at.at.x
    )
    return [
        LabelRequest(
            kind=LabelKind.CROSS_REFERENCE,
            subject=s.function,
            slot="tag",
            text=where(at, home[s.function]),
            partners=(partner,),
        )
        for s in contacts
    ]
