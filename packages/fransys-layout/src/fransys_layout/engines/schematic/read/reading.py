"""Model records to stage values, one kind of stage input per function.

Kept separate so `read/__init__.py` stays a short orchestration of one call per `StageInputs`
field (docs/design/stages.md 6, "Modules stay small and single-purpose"). `functions.py` builds one
`FunctionSpec`; `roles.py` holds the physical-net and `Role` machinery both this module and
`functions.py` need.
"""

from typing import TYPE_CHECKING, Any

from fransys_layout.engines.schematic.read.house import DEFAULT_SHEET, to_stage_profile
from fransys_layout.stages import (
    Chain,
    ChainEntry,
    Connection,
    FunctionSpec,
    GroupInfo,
    GroupSet,
    LocationInfo,
    NetGroup,
    OrderHint,
    PageHints,
    PortRef,
    Profile,
    Rail,
    SheetFormat,
    SymbolChoice,
    UnitInfo,
)
from fransys_model.derive import natural_key, schematic_functions
from fransys_model.derive.designation import bom_sort_key, unit_location
from fransys_model.derive.drawing_text import content_extent
from fransys_model.derive.drawing_text import location_path as model_location_path
from fransys_model.kernel import SchemaError
from fransys_model.layout import BreakBefore as ModelBreakBefore
from fransys_model.layout import Chain as ModelChain
from fransys_model.layout import GroupHint as ModelGroupHint
from fransys_model.layout import KeepTogether as ModelKeepTogether
from fransys_model.layout import OrderHint as ModelOrderHint
from fransys_model.layout import SheetFormat as ModelSheetFormat
from fransys_model.layout import SymbolChoice as ModelSymbolChoice
from fransys_model.layout import layout_of, profile_of
from fransys_model.vocab.enums import Aspect, ConductorKind
from fransys_model.vocab.membership import units
from fransys_model.vocab.tables import (
    aspect_nodes,
    conductors,
    functions,
    nets,
    ports,
)

from . import roles
from .functions import function_spec
from .rails import is_rail_link

if TYPE_CHECKING:
    from fransys_model.derive.indexes import Indexes
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.connectivity import Conductor


def drawn_functions(model: Model, indexes: Indexes) -> tuple[FunctionSpec, ...]:
    """Every `FunctionSpec` read from the model's drawn functions, sorted by handle."""
    drawn = set(schematic_functions(model))
    group_hints = {hint.function: hint.group for hint in layout_of(model, ModelGroupHint).values()}
    return tuple(
        sorted(
            (
                function_spec(model, indexes, function, group_hints)
                for function in functions(model).values()
                if function.id in drawn
            ),
            key=lambda spec: spec.function,
        )
    )


def terminal_sort_keys(model: Model, specs: tuple[FunctionSpec, ...]) -> dict[Id[Any], Any]:
    """Each function's item's terminal-list sort key (`bom_sort_key`, strip-qualified, D1)."""
    return {spec.function: _sort_key(model, spec) for spec in specs}


def _sort_key(model: Model, spec: FunctionSpec) -> tuple[int, Any, str, int]:
    """`bom_sort_key` of the spec's item; before numbering an empty designation's key (R5)."""
    try:
        return bom_sort_key(model, spec.item)
    except SchemaError:
        return (
            1,
            natural_key(""),
            "",
            0,
        )  # bom_sort_key's own key for an item with an empty designation


def key_orders(specs: tuple[FunctionSpec, ...]) -> dict[Id[Any], tuple[Any, ...]]:
    """Each function's authoring key in natural order (digit runs by value, layout-0165)."""
    return {spec.function: tuple(natural_key(part) for part in spec.key) for spec in specs}


def connections(model: Model, indexes: Indexes) -> tuple[Connection, ...]:
    """One `Connection` per `Conductor`, sorted by `(handle, a.port, b.port)`."""
    return tuple(
        sorted(
            (
                _connection(model, indexes, conductor)
                for conductor in conductors(model).values()
                if conductor.kind is not ConductorKind.JUMPER and not is_rail_link(model, conductor)
            ),
            key=lambda c: (c.handle, c.a.port, c.b.port),
        )
    )


def net_groups(model: Model) -> tuple[NetGroup, ...]:
    """One `NetGroup` per declared `Net`, sorted by net."""
    groups = []
    for net in nets(model).values():
        refs = tuple(
            PortRef(function=ports(model)[port_id].function, port=port_id) for port_id in net.ports
        )
        physical_net = min(roles.physical_net(model, ref.port) for ref in refs)
        groups.append(
            NetGroup(
                net=net.id,
                physical_net=physical_net,
                role=roles.NET_CLASS_TO_ROLE[net.net_class],
                ports=refs,
            )
        )
    return tuple(sorted(groups, key=lambda group: group.net))


def rails(model: Model) -> tuple[Rail, ...]:
    """Every declared `Net` with a potential, sorted by net (WP16, layout-0034 Finding 1)."""
    return tuple(
        sorted(
            (
                Rail(net=net.id, potential=net.potential, ports=net.ports)
                for net in nets(model).values()
                if net.potential is not None
            ),
            key=lambda rail: rail.net,
        )
    )


def chains(model: Model) -> tuple[Chain, ...]:
    """Every authored `layout.chain`, sorted by key."""
    return tuple(
        sorted(
            (
                Chain(
                    chain=chain.id,
                    key=chain.key,
                    entries=tuple(
                        ChainEntry(function=entry.function, index=entry.index)
                        for entry in chain.entries
                    ),
                )
                for chain in layout_of(model, ModelChain).values()
            ),
            key=lambda c: c.key,
        )
    )


def symbol_choices(model: Model) -> tuple[SymbolChoice, ...]:
    """Every authored `layout.symbol_choice`, resolved to the stage shape and sorted."""
    raw = layout_of(model, ModelSymbolChoice).values()
    explicit_functions = {choice.function for choice in raw if choice.function is not None}
    by_template: dict[Id[Any], list[ModelSymbolChoice]] = {}
    for choice in raw:
        if choice.template is not None:
            by_template.setdefault(choice.template, []).append(choice)
    entries = [
        SymbolChoice(
            choice=choice.id,
            function=choice.function,
            part=choice.part,
            kind=choice.kind.value if choice.kind is not None else None,
            symbol=choice.symbol,
            port_map=choice.port_map,
        )
        for choice in raw
        if choice.template is None
    ]
    entries.extend(
        SymbolChoice(
            choice=choice.id,
            function=function.id,
            part=None,
            kind=None,
            symbol=choice.symbol,
            port_map=choice.port_map,
        )
        for function in functions(model).values()
        if function.id not in explicit_functions and function.template is not None
        for choice in by_template.get(function.template, ())
    )
    return tuple(sorted(entries, key=lambda c: (c.choice, c.function)))


def group_infos(model: Model) -> tuple[GroupInfo, ...]:
    """Every `=` aspect node, sorted by key."""
    return tuple(
        sorted(
            (
                GroupInfo(
                    group=node.id, key=node.key, label=node.label, description=node.description
                )
                for node in aspect_nodes(model).values()
                if node.aspect is Aspect.FUNCTION
            ),
            key=lambda g: g.key,
        )
    )


def location_infos(model: Model) -> tuple[LocationInfo, ...]:
    """Every `+` aspect node, sorted by handle."""
    return tuple(
        sorted(
            (
                LocationInfo(
                    location=node.id,
                    label=node.label,
                    path=tuple(n for n, _ in location_path(model, node.id)),
                )
                for node in aspect_nodes(model).values()
                if node.aspect is Aspect.LOCATION
            ),
            key=lambda location: location.location,
        )
    )


def location_path(model: Model, location: Id[Any]) -> tuple[tuple[Id[Any], str], ...]:
    """`location`'s own root-to-leaf path of `(node handle, label)` pairs."""
    return model_location_path(model, location)


def unit_infos(model: Model) -> tuple[UnitInfo, ...]:
    """Every `Unit` in the model, sorted by handle."""
    return tuple(
        sorted(
            (
                UnitInfo(unit=unit_id, location=unit_location(model, unit_id))
                for unit_id in units(model)
            ),
            key=lambda info: info.unit,
        )
    )


def page_hints(model: Model) -> PageHints:
    """Every authored `keep_together`, `break_before` and `order_hint`."""
    return PageHints(
        keep_together=tuple(
            GroupSet(groups=kt.groups) for kt in layout_of(model, ModelKeepTogether).values()
        ),
        break_before=tuple(bb.group for bb in layout_of(model, ModelBreakBefore).values()),
        order=tuple(
            OrderHint(before=oh.before, after=oh.after)
            for oh in layout_of(model, ModelOrderHint).values()
        ),
    )


def profile_and_sheet(model: Model) -> tuple[Profile, SheetFormat, Id[Any] | None]:
    """The model's profile (`profile_of`), the `layout.sheet_format` it names and that id."""
    profile = profile_of(model)
    if profile.sheet_format is None:
        return to_stage_profile(profile), DEFAULT_SHEET, None
    sheet_record = layout_of(model, ModelSheetFormat)[profile.sheet_format]
    sheet = SheetFormat(
        name=sheet_record.name,
        content_width=content_extent(sheet_record.content_width_mm, sheet_record.module_mm),
        content_height=content_extent(sheet_record.content_height_mm, sheet_record.module_mm),
        frame_columns=sheet_record.frame_columns,
        frame_rows=sheet_record.frame_rows,
    )
    return to_stage_profile(profile), sheet, profile.sheet_format


def unused_sheet_formats(model: Model, used: Id[Any] | None) -> tuple[Id[Any], ...]:
    """The id of every authored `layout.sheet_format` other than `used`, sorted."""
    return tuple(sorted(handle for handle in layout_of(model, ModelSheetFormat) if handle != used))


def _connection(model: Model, indexes: Indexes, conductor: Conductor) -> Connection:
    """One `Connection` per `Conductor`; role from its ports' strongest."""
    role = roles.strongest(
        (
            roles.port_role(model, indexes, conductor.a),
            roles.port_role(model, indexes, conductor.b),
        )
    )
    return Connection(
        handle=conductor.id,
        physical_net=roles.physical_net(model, conductor.a),
        role=role,
        a=PortRef(function=ports(model)[conductor.a].function, port=conductor.a),
        b=PortRef(function=ports(model)[conductor.b].function, port=conductor.b),
    )
