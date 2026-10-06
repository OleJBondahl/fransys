"""Validator: aspect trees and physical containment (design/vocabulary.md 6, ROADMAP WP13)."""

from typing import TYPE_CHECKING, Any, Final

from fransys_model.kernel import Finding, Severity, key_text
from fransys_model.vocab.tables import aspect_nodes, items, placements, units

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from fransys_model.kernel import Id, Model

ASPECT_CYCLE: Final[str] = "ASPECT_CYCLE"
ASPECT_CROSS_PARENT: Final[str] = "ASPECT_CROSS_PARENT"
PLACEMENT_DUPLICATE: Final[str] = "PLACEMENT_DUPLICATE"
CONTAINMENT_CYCLE: Final[str] = "CONTAINMENT_CYCLE"
UNIT_CYCLE: Final[str] = "UNIT_CYCLE"


def _finding(code: str, subjects: Iterable[Id[Any]], message: str) -> Finding:
    return Finding(code=code, severity=Severity.ERROR, subjects=tuple(subjects), message=message)


def _cycles[K](parent_of: Mapping[Id[K], Id[K] | None]) -> list[tuple[Id[K], ...]]:
    """Every parent cycle as its members, in the order the walk met them.

    A chain that only leads into a cycle is not part of it, so it is not a member; a record
    that is its own parent is a cycle of one.
    """
    settled: set[Id[K]] = set()
    found: list[tuple[Id[K], ...]] = []
    for start in sorted(parent_of):
        path: list[Id[K]] = []
        node: Id[K] | None = start
        while node is not None and node not in settled:
            if node in path:
                found.append(tuple(path[path.index(node) :]))
                break
            path.append(node)
            node = parent_of[node]
        settled.update(path)
    return found


def _aspect_findings(model: Model) -> list[Finding]:
    nodes = aspect_nodes(model)
    found = [
        _finding(
            ASPECT_CYCLE,
            members,
            "the parent chain of aspect nodes "
            + ", ".join(sorted(nodes[member].label for member in members))
            + " loops",
        )
        for members in _cycles({node.id: node.parent for node in nodes.values()})
    ]
    for node in nodes.values():
        parent = None if node.parent is None else nodes[node.parent]
        if parent is not None and parent.aspect is not node.aspect:
            message = (
                f"{node.aspect.value} node {node.label} is parented under "
                f"{parent.aspect.value} node {parent.label}"
            )
            found.append(_finding(ASPECT_CROSS_PARENT, (node.id, parent.id), message))
    return found


def _placement_findings(model: Model) -> list[Finding]:
    nodes = aspect_nodes(model)
    by_item_aspect: dict[tuple[Id[Any], str], list[Id[Any]]] = {}
    for placement in placements(model).values():
        aspect = nodes[placement.node].aspect.value
        by_item_aspect.setdefault((placement.item, aspect), []).append(placement.id)
    all_items = items(model)
    return [
        _finding(
            PLACEMENT_DUPLICATE,
            (item, *placed),
            f"item {key_text(all_items[item])} is placed {len(placed)} times "
            f"in the {aspect} aspect",
        )
        for (item, aspect), placed in by_item_aspect.items()
        if len(placed) > 1
    ]


def _containment_findings(model: Model) -> list[Finding]:
    all_items = items(model)
    return [
        _finding(
            CONTAINMENT_CYCLE,
            members,
            "the parent chain of items "
            + ", ".join(sorted(key_text(all_items[member]) for member in members))
            + " loops",
        )
        for members in _cycles({item.id: item.parent for item in all_items.values()})
    ]


def _unit_findings(model: Model) -> list[Finding]:
    all_units = units(model)
    return [
        _finding(
            UNIT_CYCLE,
            members,
            "the parent chain of units "
            + ", ".join(sorted(key_text(all_units[member]) for member in members))
            + " loops",
        )
        for members in _cycles({unit.id: unit.parent for unit in all_units.values()})
    ]


def check_structure(model: Model) -> tuple[Finding, ...]:
    """Check aspect trees are acyclic and single-aspect, placements unique, containment acyclic.

    All five codes are `ERROR`; a cycle code is one finding per parent cycle, subjects its members.
    The other two: one per node or item; sorted by `(code, subjects, message)`.
    """
    found = [
        *_aspect_findings(model),
        *_placement_findings(model),
        *_containment_findings(model),
        *_unit_findings(model),
    ]
    return tuple(sorted(found, key=lambda f: (f.code, f.subjects, f.message)))
