"""The overview's two regroupings of the model: the unit matrix and the Signals lens.

Reached as `derive.unit_matrix` and `derive.signal_lens` (model-0197).
"""

from fransys_model.vocab.tables import functions
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Item

from .designation import printed_designation
from .kinds import signal_kind
from .order import plc_racks
from .overview_field import field_devices
from .overview_levels import overview_level
from .plc_rack import plc_rack_modules
from .rows import LensChannel, LensModule, MatrixCell, UnitMatrix

__all__ = ["signal_lens", "unit_matrix"]


def unit_matrix(model: Model) -> UnitMatrix:
    """Every system-level box against every other, with the cables.

    The axis is the system level's boxes in box text order, less every unit's field devices
    (`field_devices`). A cell has `row < col` and counts the
    distinct cables whose lines join those two boxes; a pair with no cable has no cell. The
    counts come from the same lines the system level draws, so the matrix cannot disagree.
    """
    level = overview_level(model, None)
    folded = field_devices(model)
    axis = tuple(one for one in level.boxes if one.box not in folded)
    place = {one.box: index for index, one in enumerate(axis)}
    found: dict[tuple[int, int], set[Id[Item]]] = {}
    for line in level.lines:
        if line.ref.a not in place or line.ref.b not in place:
            continue
        row, col = sorted((place[line.ref.a], place[line.ref.b]))
        if line.ref.via is not None:
            found.setdefault((row, col), set()).add(line.ref.via)
    cells = tuple(
        MatrixCell(row=row, col=col, count=len(cables), cables=tuple(sorted(cables)))
        for (row, col), cables in sorted(found.items())
    )
    return UnitMatrix(axis=axis, cells=cells)


def signal_lens(model: Model) -> tuple[LensModule, ...]:
    """The PLC modules with their channels and field devices.

    Racks in designation order, then `plc_rack_modules`' physical order within each, so the lens
    reads the rack as the PLC list does. Each channel carries `signal_kind` of its signal type.
    A module with no channel is not listed. Raises `SchemaError`, as `plc_rack_modules` does,
    for a module or device with no designation.
    """
    return tuple(one for one in _lens_modules(model) if one.channels)


def _lens_modules(model: Model) -> tuple[LensModule, ...]:
    all_functions = functions(model)
    return tuple(
        LensModule(
            module=module.module,
            designation=module.designation,
            channels=tuple(
                LensChannel(
                    channel=channel.channel,
                    number=channel.number,
                    kind=signal_kind(channel.signal),
                    signal_name=channel.signal_name,
                    device=channel.field_device,
                    device_item=(
                        None
                        if channel.field_device is None
                        else all_functions[channel.field_device].item
                    ),
                    device_designation=channel.field_device_designation,
                )
                for channel in module.channels
            ),
        )
        for rack in sorted(
            plc_racks(model), key=lambda rack: (printed_designation(model, rack), rack)
        )
        for module in plc_rack_modules(model, rack)
    )
