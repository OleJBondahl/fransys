"""The `=` group each drawn function lands in, and so which groups draw anything (model-0441, model-0442)."""

from fransys_model.derive.indexes import build_indexes
from fransys_model.derive.lookups import effective_placement
from fransys_model.derive.placement_reads import function_item
from fransys_model.derive.structure import schematic_functions
from fransys_model.kernel import DIGEST_CACHE_SIZE, digest_cached
from fransys_model.layout import GroupHint, layout_of
from fransys_model.vocab import Aspect, FunctionKind
from fransys_model.vocab.tables import conductors, functions, ports
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab import AspectNode, Function

__all__ = ["function_group", "function_moves", "group_draws", "group_members_drawn_in"]


@digest_cached(DIGEST_CACHE_SIZE)
def _hinted(model: Model) -> dict[Id[Function], Id[AspectNode]]:
    return {h.function: h.group for h in layout_of(model, GroupHint).values()}


def _placed(model: Model, function: Id[Function]) -> Id[AspectNode] | None:
    return effective_placement(model, function_item(model, function), Aspect.FUNCTION)


# The kinds drawn with their item, never with the block of their wires (author-0050, which model-0442 supersedes; R1855).
_DRAWN_WITH_ITEM = frozenset(
    {FunctionKind.TERMINAL, FunctionKind.SUPPLY, FunctionKind.CONNECTOR, FunctionKind.PLC_CHANNEL},
)


@digest_cached(DIGEST_CACHE_SIZE)
def _wired_blocks(model: Model) -> dict[Id[Function], tuple[Id[AspectNode], ...]]:
    """Per function, the function blocks its wires were authored in (`Conductor.block`), first seen first."""
    found: dict[Id[Function], dict[Id[AspectNode], None]] = {}
    for conductor in conductors(model).values():
        if conductor.block is not None:
            for end in (conductor.a, conductor.b):
                found.setdefault(ports(model)[end].function, {})[conductor.block] = None
    return {function: tuple(blocks) for function, blocks in found.items()}


@digest_cached(DIGEST_CACHE_SIZE)
def _home_groups(model: Model) -> frozenset[Id[AspectNode]]:
    """The groups an item placed there has a drawn function in: the groups that draw by home membership."""
    return frozenset(g for f in schematic_functions(model) if (g := _placed(model, f)) is not None)


def _wired_group(model: Model, function: Id[Function], blocks: tuple[Id[AspectNode], ...]) -> Id[AspectNode] | None:
    """The one block that wires `function`, when it differs from its home and draws (model-0442); else none."""
    home, record = _placed(model, function), functions(model)[function]
    if (
        len(blocks) != 1
        or home is None
        or blocks[0] == home
        or record.kind in _DRAWN_WITH_ITEM
        or len(build_indexes(model).functions_by_item[record.item]) <= 1
    ):
        return None
    return blocks[0] if blocks[0] in _home_groups(model) else None


@digest_cached(DIGEST_CACHE_SIZE)
def function_moves(model: Model) -> dict[Id[Function], Id[AspectNode]]:
    """Each function drawn away from its home: the block its wires were authored in, then its `GroupHint` (which wins)."""
    wired = {f: g for f, blocks in _wired_blocks(model).items() if (g := _wired_group(model, f, blocks)) is not None}
    return wired | _hinted(model)


def function_group(model: Model, function: Id[Function]) -> Id[AspectNode] | None:
    """The `=` node `function` is drawn in: its move (`function_moves`), else its item's placement."""
    return function_moves(model).get(function) or _placed(model, function)


@digest_cached(DIGEST_CACHE_SIZE)
def _drawn(model: Model) -> tuple[tuple[Id[AspectNode] | None, Id[AspectNode] | None], ...]:
    """Per drawn function in `Id` order, the group it is placed in and the group it is drawn in."""
    return tuple((_placed(model, f), function_group(model, f)) for f in schematic_functions(model))


def group_draws(model: Model, group: Id[AspectNode]) -> bool:
    """Whether any drawn function lands in `group`: false for a group whose members are drawn elsewhere or never."""
    return any(drawn == group for _, drawn in _drawn(model))


def group_members_drawn_in(model: Model, group: Id[AspectNode]) -> tuple[Id[AspectNode], ...]:
    """The other groups the functions placed in `group` are drawn in (by a `GroupHint`), first seen first."""
    return tuple(dict.fromkeys(drawn for placed, drawn in _drawn(model) if placed == group and drawn not in (None, group)))
