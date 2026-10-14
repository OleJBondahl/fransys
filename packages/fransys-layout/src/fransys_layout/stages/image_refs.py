"""Contact images: who owns a contact, and each contact's reference to its home."""

from typing import TYPE_CHECKING

from .types import Home, LabelKind, LabelRequest, RequestPartner

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from fransys_model.kernel import AuthoringKey

    from .types import Column, FunctionSpec, Handle, PlacedFunction


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
    """The owners whose coils are all unplaced: their contacts get no reference."""
    coils = {
        o: [s for s in g if s.roles.contacts_apart] for o, g in by_owner(specs, owners).items()
    }
    return {o for o, c in coils.items() if c and not any(s.function in home for s in c)}


def home_references(
    contacts: Sequence[FunctionSpec],
    main: FunctionSpec,
    home: Mapping[Handle, PlacedFunction],
    where: Callable[[PlacedFunction, PlacedFunction], str],
) -> list[LabelRequest]:
    """Each contact's reference to `main` (its coil, else the device's main symbol)."""
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


def replica_cells(columns: Sequence[Column]) -> dict[tuple[AuthoringKey, Handle], Handle | None]:
    """layout-0184: `(column key, function)` of each cell drawn away from its home -> its unit."""
    return {
        (column.key, cell.function): column.unit
        for column in columns
        for cell in column.cells
        if cell.home is Home.ELSEWHERE
    }


def home_placements(
    pages: Sequence[tuple[tuple[PlacedFunction, ...], tuple[object, ...]]],
    replicas: Mapping[tuple[AuthoringKey, Handle], Handle | None],
    units: Mapping[Handle, Handle | None],
) -> dict[Handle, PlacedFunction]:
    """Each function's home placement; with no home drawn, a replica of its own unit, else any."""
    home: dict[Handle, PlacedFunction] = {}
    tier: dict[Handle, int] = {}
    for placed, _ in pages:
        for one in placed:
            at = (one.column, one.function)
            rank = 0 if at not in replicas else 1 if replicas[at] == units.get(one.function) else 2
            if rank < tier.get(one.function, 3):  # the first placement of the best tier wins
                home[one.function], tier[one.function] = one, rank
    return home
