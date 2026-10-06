"""Test setup: add the bare records a fixture refers to but does not define.

`freeze()` resolves every reference, and some fixtures name ports, items or parts by a
hand-made id without building the record. `scaffold` builds the missing `Item`, `Function`,
`Port` and `Part` records, bare and installed, and leaves every other kind (an `AspectNode`,
whose aspect a test must choose) to the test. It never touches a record the fixture defines.
"""

from typing import Any

from fransys_model.kernel import Id, Record, field_specs
from fransys_model.vocab.core import Function, Item, Port
from fransys_model.vocab.enums import FunctionKind, PartCategory, PortRole
from fransys_model.vocab.templates import Part

SCAFFOLD_ITEM: Id[Item] = Id(kind="item", value="0" * 32)
SCAFFOLD_FUNCTION: Id[Function] = Id(kind="function", value="0" * 32)


def _references(record: Record) -> set[Id[Any]]:
    found: set[Any] = set()  # getattr values: an optional ref field can hold None
    for spec in field_specs(type(record)):
        if spec.ref_kind is None:
            continue
        value = getattr(record, spec.name)
        found.update(value if isinstance(value, tuple) else [value])
    return {target for target in found if isinstance(target, Id)}


def _bare(missing: Id[Any], number: int) -> Record | None:
    key = ("scaffold", missing.kind, str(number))
    match missing.kind:
        case "item":
            return Item(
                id=missing,
                key=key,
                part=None,
                parent=None,
                position=None,
                tag=None,
                description="Scaffold",
                installed=True,
            )
        case "function":
            return Function(
                id=missing,
                key=key,
                item=SCAFFOLD_ITEM,
                template=None,
                name=f"f{number}",
                kind=FunctionKind.GENERIC,
            )
        case "port":
            return Port(
                id=missing,
                key=key,
                function=SCAFFOLD_FUNCTION,
                template=None,
                name=f"p{number}",
                role=PortRole.GENERIC,
            )
        case "part":
            return Part(
                id=missing,
                key=key,
                mpn=f"SCAFFOLD-{number}",
                manufacturer="Scaffold",
                description="Scaffold",
                category=PartCategory.GENERIC,
                class_code="X",
            )
        case _:
            return None


def scaffold(records: tuple[Record, ...]) -> tuple[Record, ...]:
    """The records to add so that every reference of `records` that can be built resolves."""
    present = {record.id for record in records}
    everything: list[Record] = list(records)
    added: list[Record] = []
    unbuildable: set[Id[Any]] = set()
    while True:
        missing = sorted(
            {target for record in everything for target in _references(record)}
            - present
            - unbuildable
        )
        if not missing:
            return tuple(added)
        for number, target in enumerate(missing, start=len(added)):
            bare = _bare(target, number)
            if bare is None:
                unbuildable.add(target)
                continue
            added.append(bare)
            everything.append(bare)
            present.add(target)
