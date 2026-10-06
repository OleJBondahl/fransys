"""Diff of the unit, item, nested-unit and boundary sections (baseline spec M1)."""

from typing import TYPE_CHECKING, cast

from .baseline_codec import _decimal_dict
from .natural_order import natural_key
from .revision_text import revision_text
from .rows import (
    BaselineBoundary,
    BaselineItem,
    BaselineNestedUnit,
    BaselineUnit,
    Change,
)

if TYPE_CHECKING:
    from fransys_model.vocab.ratings import Operating, Rating


def _release_field_changes(
    section: str,
    subject: str,
    parts: tuple[str, ...],
    a: tuple[str, int, int],
    b: tuple[str, int, int],
) -> list[Change]:
    """A `changed` row for each of `interface`, `revision`, `version` that differs.

    `a`/`b` are each `(interface, version, revision)`, the fields `unit` and `units` diff alike.
    `revision` and `version` rows both print the release's pair through `revision_text`.
    """
    a_interface, a_version, a_revision = a
    b_interface, b_version, b_revision = b
    rows: list[Change] = []
    if a_interface != b_interface:
        rows.append(
            Change(
                section=section,
                change="changed",
                subject=subject,
                field="interface",
                before=a_interface,
                after=b_interface,
                parts=parts,
                detail="",
            )
        )
    if a_revision != b_revision:
        rows.append(
            Change(
                section=section,
                change="changed",
                subject=subject,
                field="revision",
                before=revision_text(a_version, a_revision),
                after=revision_text(b_version, b_revision),
                parts=parts,
                detail="",
            )
        )
    if a_version != b_version:
        rows.append(
            Change(
                section=section,
                change="changed",
                subject=subject,
                field="version",
                before=revision_text(a_version, a_revision),
                after=revision_text(b_version, b_revision),
                parts=parts,
                detail="",
            )
        )
    return rows


def _unit_changes(a: BaselineUnit, b: BaselineUnit) -> list[Change]:
    return _release_field_changes(
        "unit",
        a.name,
        (a.name,),
        (a.interface, a.version, a.revision),
        (b.interface, b.version, b.revision),
    )


def unit_subject_text(unit: BaselineUnit) -> str:
    """The subject of a Change on a `""` row: `<name> <V>.<R>` (model-0132; L2 leaves it blank)."""
    return f"{unit.name} {revision_text(unit.version, unit.revision)}"


def _by_subject[R: BaselineItem | BaselineBoundary](
    rows: tuple[R, ...], unit_subject: str
) -> dict[str, R]:
    return {r.designation or unit_subject: r for r in rows}


def _item_field_text(field: str, value: object) -> str:
    if field in ("mpn", "manufacturer"):
        return cast("str", value)
    if field in ("installed", "external"):
        return str(value)
    # `position` is the only remaining field, `int | None`.
    return "" if value is None else str(value)


def _item_changes(
    a_rows: tuple[BaselineItem, ...], b_rows: tuple[BaselineItem, ...], unit_subject: str
) -> list[Change]:
    a_index = _by_subject(a_rows, unit_subject)
    b_index = _by_subject(b_rows, unit_subject)
    changes: list[Change] = []
    for designation in set(a_index) - set(b_index):
        r = a_index[designation]
        changes.append(
            Change(
                section="items",
                change="removed",
                subject=designation,
                field="",
                before="",
                after="",
                parts=(designation,),
                detail=f"{r.mpn}, {r.manufacturer}",
            )
        )
    for designation in set(b_index) - set(a_index):
        r = b_index[designation]
        changes.append(
            Change(
                section="items",
                change="added",
                subject=designation,
                field="",
                before="",
                after="",
                parts=(designation,),
                detail=f"{r.mpn}, {r.manufacturer}",
            )
        )
    for designation in set(a_index) & set(b_index):
        a_row, b_row = a_index[designation], b_index[designation]
        for field in ("external", "installed", "manufacturer", "mpn", "position"):
            a_val, b_val = getattr(a_row, field), getattr(b_row, field)
            if a_val != b_val:
                changes.append(
                    Change(
                        section="items",
                        change="changed",
                        subject=designation,
                        field=field,
                        before=_item_field_text(field, a_val),
                        after=_item_field_text(field, b_val),
                        parts=(designation,),
                        detail="",
                    )
                )
    changes.sort(key=lambda c: (natural_key(c.subject), c.field))
    return changes


def _nested_unit_index(
    rows: tuple[BaselineNestedUnit, ...],
) -> dict[tuple[str, str], BaselineNestedUnit]:
    index: dict[tuple[str, str], BaselineNestedUnit] = {}
    for row in rows:
        for instance in row.instances:
            index[(row.name, instance)] = row
    return index


def _nested_unit_changes(
    a_rows: tuple[BaselineNestedUnit, ...], b_rows: tuple[BaselineNestedUnit, ...]
) -> list[Change]:
    a_index = _nested_unit_index(a_rows)
    b_index = _nested_unit_index(b_rows)
    changes: list[Change] = []
    for key in set(a_index) - set(b_index):
        name, instance = key
        changes.append(
            Change(
                section="units",
                change="removed",
                subject=f"{name} {instance}",
                field="",
                before="",
                after="",
                parts=(instance, name),
                detail="",
            )
        )
    for key in set(b_index) - set(a_index):
        name, instance = key
        changes.append(
            Change(
                section="units",
                change="added",
                subject=f"{name} {instance}",
                field="",
                before="",
                after="",
                parts=(instance, name),
                detail="",
            )
        )
    for key in set(a_index) & set(b_index):
        name, instance = key
        a_row, b_row = a_index[key], b_index[key]
        changes.extend(
            _release_field_changes(
                "units",
                f"{name} {instance}",
                (instance, name),
                (a_row.interface, a_row.version, a_row.revision),
                (b_row.interface, b_row.version, b_row.revision),
            )
        )
    changes.sort(key=lambda c: (natural_key(c.subject), c.field))
    return changes


def _boundary_changes(
    a_rows: tuple[BaselineBoundary, ...], b_rows: tuple[BaselineBoundary, ...], unit_subject: str
) -> list[Change]:
    a_index = _by_subject(a_rows, unit_subject)
    b_index = _by_subject(b_rows, unit_subject)
    changes: list[Change] = []
    for designation in set(a_index) - set(b_index):
        r = a_index[designation]
        changes.append(
            Change(
                section="boundary",
                change="removed",
                subject=designation,
                field="",
                before="",
                after="",
                parts=(designation,),
                detail="ports " + ", ".join(sorted(r.ports, key=natural_key)),
            )
        )
    for designation in set(b_index) - set(a_index):
        r = b_index[designation]
        changes.append(
            Change(
                section="boundary",
                change="added",
                subject=designation,
                field="",
                before="",
                after="",
                parts=(designation,),
                detail="ports " + ", ".join(sorted(r.ports, key=natural_key)),
            )
        )
    for designation in set(a_index) & set(b_index):
        a_row, b_row = a_index[designation], b_index[designation]
        if a_row.ports != b_row.ports:
            a_ports, b_ports = set(a_row.ports), set(b_row.ports)
            changes.extend(
                Change(
                    section="boundary",
                    change="added",
                    subject=designation,
                    field="ports",
                    before="",
                    after=port,
                    parts=(designation,),
                    detail="",
                )
                for port in sorted(b_ports - a_ports, key=natural_key)
            )
            changes.extend(
                Change(
                    section="boundary",
                    change="removed",
                    subject=designation,
                    field="ports",
                    before=port,
                    after="",
                    parts=(designation,),
                    detail="",
                )
                for port in sorted(a_ports - b_ports, key=natural_key)
            )
        changes.extend(_rating_changes(designation, "rating", a_row.rating, b_row.rating))
        changes.extend(_rating_changes(designation, "operating", a_row.operating, b_row.operating))
    changes.sort(key=lambda c: (natural_key(c.subject), c.field))
    return changes


def _rating_changes(
    designation: str, prefix: str, a: Rating | Operating | None, b: Rating | Operating | None
) -> list[Change]:
    """One `changed` row per key of `a`/`b` (M1) that differs, field `<prefix>.<key>`."""
    a_dict, b_dict = _decimal_dict(a) or {}, _decimal_dict(b) or {}
    return [
        Change(
            section="boundary",
            change="changed",
            subject=designation,
            field=f"{prefix}.{key}",
            before=cast("str", a_dict.get(key) or ""),
            after=cast("str", b_dict.get(key) or ""),
            parts=(designation,),
            detail="",
        )
        for key in sorted(set(a_dict) | set(b_dict))
        if a_dict.get(key) != b_dict.get(key)
    ]
