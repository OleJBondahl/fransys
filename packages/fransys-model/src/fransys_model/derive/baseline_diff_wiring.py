"""Diff of the conductor, mate and net sections."""

from typing import TYPE_CHECKING, cast

from .baseline_diff_rows import presence_changes, sort_changes
from .list_cells import CELL_SEPARATOR
from .order import natural_key
from .rows_baseline import Change

if TYPE_CHECKING:
    from .rows_baseline import BaselineConductor, BaselineMate, BaselineNet


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


def _ends(_key: object, row: BaselineConductor | BaselineMate) -> tuple[str, tuple[str, ...], str]:
    return f"{row.a} {row.b}", (row.a, row.b), ""


def _conductor_changes(
    a_rows: tuple[BaselineConductor, ...],
    b_rows: tuple[BaselineConductor, ...],
    *,
    keyed: bool = False,
) -> list[Change]:
    a_index = {_end_ident(r, keyed=keyed): r for r in a_rows}
    b_index = {_end_ident(r, keyed=keyed): r for r in b_rows}
    changes = presence_changes("conductors", a_index, b_index, _ends)
    for key in set(a_index) & set(b_index):
        a_row, b_row = a_index[key], b_index[key]
        subject = f"{b_row.a} {b_row.b}"
        for field in ("carrier", "colour", "gauge_mm2", "kind", "label", "length_mm"):
            a_val, b_val = getattr(a_row, field), getattr(b_row, field)
            if a_val != b_val:
                before, after = _conductor_field_text(field, a_val), _conductor_field_text(field, b_val)
                changes.append(
                    Change(
                        section="conductors",
                        change="changed",
                        subject=subject,
                        parts=(b_row.a, b_row.b),
                        field=field,
                        before=before,
                        after=after,
                        detail="",
                    )
                )
    return sort_changes(changes)


def _mate_changes(a_rows: tuple[BaselineMate, ...], b_rows: tuple[BaselineMate, ...], *, keyed: bool = False) -> list[Change]:
    a_index = {_end_ident(r, keyed=keyed): r for r in a_rows}
    b_index = {_end_ident(r, keyed=keyed): r for r in b_rows}
    return sort_changes(presence_changes("mates", a_index, b_index, _ends))


def _net_members(record: BaselineNet, *, keyed: bool) -> tuple[str, ...] | frozenset[tuple[str, str]]:
    """The members of a net: item key and pin when keyed, else the printed ports."""
    if keyed and record.port_keys:
        return frozenset(zip(record.port_keys, record.port_pins, strict=True))
    return record.ports


def _net_key(record: BaselineNet, *, keyed: bool) -> object:
    return record.name if record.name is not None else _net_members(record, keyed=keyed)


def _net_subject(record: BaselineNet) -> str:
    return record.name if record.name is not None else " ".join(record.ports)


def _net_ident(_key: object, record: BaselineNet) -> tuple[str, tuple[str, ...], str]:
    subject = _net_subject(record)
    return subject, (subject,), ""


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
        moved = _net_members(a_row, keyed=keyed) != _net_members(b_row, keyed=keyed) if field == "ports" else a_val != b_val
        if moved:
            before, after = _net_field_text(field, a_val), _net_field_text(field, b_val)
            changes.append(
                Change(section="nets", change="changed", subject=subject, parts=(subject,), field=field, before=before, after=after, detail="")
            )
    return changes


def _net_changes(a_rows: tuple[BaselineNet, ...], b_rows: tuple[BaselineNet, ...], *, keyed: bool = False) -> list[Change]:
    a_index = {_net_key(r, keyed=keyed): r for r in a_rows}
    b_index = {_net_key(r, keyed=keyed): r for r in b_rows}
    changes = presence_changes("nets", a_index, b_index, _net_ident)
    for key in set(a_index) & set(b_index):
        changes.extend(_net_field_changes(a_index[key], b_index[key], keyed=keyed))
    return sort_changes(changes)
