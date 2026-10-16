"""Diff of the conductor, mate and net sections."""

from typing import cast

from .list_cells import CELL_SEPARATOR
from .order import natural_key
from .rows_baseline import BaselineConductor, BaselineMate, BaselineNet, Change


def _conductor_field_text(field: str, value: object) -> str:
    if field == "kind":
        return cast("str", value)
    if field == "length_mm":
        return "" if value is None else str(value)
    # carrier, colour, gauge_mm2, label: str | None
    return "" if value is None else cast("str", value)


def _end_ident(row: BaselineConductor | BaselineMate, *, keyed: bool) -> tuple[str | None, ...]:
    """A wire's identity: its ends' item keys and pins when keyed, else its printed ends."""
    if keyed and row.a_key is not None:
        return (row.a_key, row.a_pin, row.b_key, row.b_pin)
    return (row.a, row.b)


def _conductor_changes(
    a_rows: tuple[BaselineConductor, ...],
    b_rows: tuple[BaselineConductor, ...],
    *,
    keyed: bool = False,
) -> list[Change]:
    a_index = {_end_ident(r, keyed=keyed): r for r in a_rows}
    b_index = {_end_ident(r, keyed=keyed): r for r in b_rows}
    changes: list[Change] = []
    for key in set(a_index) - set(b_index):
        r = a_index[key]
        changes.append(
            Change(
                section="conductors",
                change="removed",
                subject=f"{r.a} {r.b}",
                field="",
                before="",
                after="",
                parts=(r.a, r.b),
                detail="",
            )
        )
    for key in set(b_index) - set(a_index):
        r = b_index[key]
        changes.append(
            Change(
                section="conductors",
                change="added",
                subject=f"{r.a} {r.b}",
                field="",
                before="",
                after="",
                parts=(r.a, r.b),
                detail="",
            )
        )
    for key in set(a_index) & set(b_index):
        a_row, b_row = a_index[key], b_index[key]
        subject = f"{b_row.a} {b_row.b}"
        for field in ("carrier", "colour", "gauge_mm2", "kind", "label", "length_mm"):
            a_val, b_val = getattr(a_row, field), getattr(b_row, field)
            if a_val != b_val:
                changes.append(
                    Change(
                        section="conductors",
                        change="changed",
                        subject=subject,
                        field=field,
                        before=_conductor_field_text(field, a_val),
                        after=_conductor_field_text(field, b_val),
                        parts=(b_row.a, b_row.b),
                        detail="",
                    )
                )
    changes.sort(key=lambda c: (natural_key(c.subject), c.field))
    return changes


def _mate_changes(
    a_rows: tuple[BaselineMate, ...], b_rows: tuple[BaselineMate, ...], *, keyed: bool = False
) -> list[Change]:
    a_index = {_end_ident(r, keyed=keyed): r for r in a_rows}
    b_index = {_end_ident(r, keyed=keyed): r for r in b_rows}
    changes: list[Change] = []
    for key in set(a_index) - set(b_index):
        r = a_index[key]
        changes.append(
            Change(
                section="mates",
                change="removed",
                subject=f"{r.a} {r.b}",
                field="",
                before="",
                after="",
                parts=(r.a, r.b),
                detail="",
            )
        )
    for key in set(b_index) - set(a_index):
        r = b_index[key]
        changes.append(
            Change(
                section="mates",
                change="added",
                subject=f"{r.a} {r.b}",
                field="",
                before="",
                after="",
                parts=(r.a, r.b),
                detail="",
            )
        )
    changes.sort(key=lambda c: (natural_key(c.subject), c.field))
    return changes


def _net_members(
    record: BaselineNet, *, keyed: bool
) -> tuple[str, ...] | frozenset[tuple[str, str]]:
    """The members of a net: item key and pin when keyed, else the printed ports."""
    if keyed and record.port_keys:
        return frozenset(zip(record.port_keys, record.port_pins, strict=True))
    return record.ports


def _net_key(record: BaselineNet, *, keyed: bool) -> object:
    return record.name if record.name is not None else _net_members(record, keyed=keyed)


def _net_subject(record: BaselineNet) -> str:
    return record.name if record.name is not None else " ".join(record.ports)


def _net_field_text(field: str, value: object) -> str:
    if field == "class":
        return cast("str", value)
    if field == "potential":
        return "" if value is None else cast("str", value)
    # ports: the row's own `ports` tuple
    return CELL_SEPARATOR.join(sorted(cast("tuple[str, ...]", value), key=natural_key))


def _net_field_changes(a_row: BaselineNet, b_row: BaselineNet, *, keyed: bool) -> list[Change]:
    """The `changed` rows of one net present in both listings: ports, class, potential."""
    subject = _net_subject(b_row)
    changes: list[Change] = []
    for field, attr in (("ports", "ports"), ("class", "net_class"), ("potential", "potential")):
        a_val, b_val = getattr(a_row, attr), getattr(b_row, attr)
        if field == "ports":
            moved = _net_members(a_row, keyed=keyed) != _net_members(b_row, keyed=keyed)
        else:
            moved = a_val != b_val
        if moved:
            changes.append(
                Change(
                    section="nets",
                    change="changed",
                    subject=subject,
                    field=field,
                    before=_net_field_text(field, a_val),
                    after=_net_field_text(field, b_val),
                    parts=(subject,),
                    detail="",
                )
            )
    return changes


def _net_changes(
    a_rows: tuple[BaselineNet, ...], b_rows: tuple[BaselineNet, ...], *, keyed: bool = False
) -> list[Change]:
    a_index = {_net_key(r, keyed=keyed): r for r in a_rows}
    b_index = {_net_key(r, keyed=keyed): r for r in b_rows}
    changes: list[Change] = []
    for key in set(a_index) - set(b_index):
        subject = _net_subject(a_index[key])
        changes.append(
            Change(
                section="nets",
                change="removed",
                subject=subject,
                field="",
                before="",
                after="",
                parts=(subject,),
                detail="",
            )
        )
    for key in set(b_index) - set(a_index):
        subject = _net_subject(b_index[key])
        changes.append(
            Change(
                section="nets",
                change="added",
                subject=subject,
                field="",
                before="",
                after="",
                parts=(subject,),
                detail="",
            )
        )
    for key in set(a_index) & set(b_index):
        changes.extend(_net_field_changes(a_index[key], b_index[key], keyed=keyed))
    changes.sort(key=lambda c: (natural_key(c.subject), c.field))
    return changes
