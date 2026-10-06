"""Diff of the conductor, mate and net sections (baseline spec M1)."""

from typing import cast

from .list_cells import CELL_SEPARATOR
from .natural_order import natural_key
from .rows import (
    BaselineConductor,
    BaselineMate,
    BaselineNet,
    Change,
)


def _conductor_field_text(field: str, value: object) -> str:
    if field == "kind":
        return cast("str", value)
    if field == "length_mm":
        return "" if value is None else str(value)
    # carrier, colour, gauge_mm2, label: str | None
    return "" if value is None else cast("str", value)


def _conductor_changes(
    a_rows: tuple[BaselineConductor, ...], b_rows: tuple[BaselineConductor, ...]
) -> list[Change]:
    a_index = {(r.a, r.b): r for r in a_rows}
    b_index = {(r.a, r.b): r for r in b_rows}
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
        subject = f"{a_row.a} {a_row.b}"
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
                        parts=(a_row.a, a_row.b),
                        detail="",
                    )
                )
    changes.sort(key=lambda c: (natural_key(c.subject), c.field))
    return changes


def _mate_changes(
    a_rows: tuple[BaselineMate, ...], b_rows: tuple[BaselineMate, ...]
) -> list[Change]:
    a_index = {(r.a, r.b): r for r in a_rows}
    b_index = {(r.a, r.b): r for r in b_rows}
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


def _net_key(record: BaselineNet) -> str | tuple[str, ...]:
    return record.name if record.name is not None else record.ports


def _net_subject(record: BaselineNet) -> str:
    return record.name if record.name is not None else " ".join(record.ports)


def _net_field_text(field: str, value: object) -> str:
    if field == "class":
        return cast("str", value)
    if field == "potential":
        return "" if value is None else cast("str", value)
    # ports: the row's own `ports` tuple
    return CELL_SEPARATOR.join(sorted(cast("tuple[str, ...]", value)))


def _net_changes(a_rows: tuple[BaselineNet, ...], b_rows: tuple[BaselineNet, ...]) -> list[Change]:
    a_index = {_net_key(r): r for r in a_rows}
    b_index = {_net_key(r): r for r in b_rows}
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
        a_row, b_row = a_index[key], b_index[key]
        subject = _net_subject(a_row)
        for field, attr in (
            ("ports", "ports"),
            ("class", "net_class"),
            ("potential", "potential"),
        ):
            a_val, b_val = getattr(a_row, attr), getattr(b_row, attr)
            if a_val != b_val:
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
    changes.sort(key=lambda c: (natural_key(c.subject), c.field))
    return changes
