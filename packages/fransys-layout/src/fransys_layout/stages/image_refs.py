"""Contact images: who owns a contact, and each contact's reference to its home."""

from typing import TYPE_CHECKING

from fransys_model.derive.drawing_text import frame_row

from .types import Home, LabelKind, LabelRequest, RequestPartner

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from fransys_model.kernel import AuthoringKey

    from .types import Column, FunctionSpec, Handle, PlacedFunction, SheetFormat


def listed(spec: FunctionSpec) -> bool:
    """A function a contact list names: a contact, or a switch of a group (layout-0237)."""
    return spec.roles.contact or spec.switch_group is not None


def holds_list(spec: FunctionSpec) -> bool:
    """A function a contact list stands under: a coil or a box, or a group's lead switch."""
    return spec.roles.contacts_apart or (spec.switch_group is not None and spec.actuator)


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
    coils = {o: [s for s in g if holds_list(s)] for o, g in by_owner(specs, owners).items()}
    return {o for o, c in coils.items() if c and not any(s.function in home for s in c)}


def one_per_row(
    contacts: Sequence[FunctionSpec],
    home: Mapping[Handle, PlacedFunction],
    linked: frozenset[Handle],
    sheet: SheetFormat,
) -> list[FunctionSpec]:
    """`contacts` less the pole-linked ones that stand in one row after the leftmost (layout-0235).

    A repeat would print the same reference beside the same tag; the leftmost one keeps it.
    """
    dropped: set[Handle] = set()
    seen: set[tuple[int, int, str]] = set()
    for spec in sorted(contacts, key=lambda s: (home[s.function].at.x, s.function)):
        if spec.function not in linked:
            continue
        one = home[spec.function]
        place = (
            one.drawing_set,
            one.page,
            frame_row(sheet.content_height, sheet.frame_rows, one.at.y),
        )
        if place in seen:
            dropped.add(spec.function)
        seen.add(place)
    return [s for s in contacts if s.function not in dropped]


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


def member_partners(at: PlacedFunction, spec: FunctionSpec) -> tuple[RequestPartner, ...]:
    """A contact's table partners at `at`: one per member of a group, its first port (0227)."""
    firsts = {port.pole: port.port for port in reversed(spec.ports)}
    poles = range(len(spec.gang)) if spec.gang else (None,)
    return tuple(
        RequestPartner(
            port=spec.ports[0].port if pole is None else firsts[pole],
            drawing_set=at.drawing_set,
            page=at.page,
            x=at.at.x,
        )
        for pole in poles
    )


def table_partners(
    contacts: Sequence[FunctionSpec], home: Mapping[Handle, PlacedFunction], coil: FunctionSpec
) -> tuple[RequestPartner, ...]:
    """A contact table's partners, each contact's at its home; with none, the coil's own."""
    found = tuple(p for s in contacts for p in member_partners(home[s.function], s))
    return found or member_partners(home[coil.function], coil)
