"""A small invented plant on three power nets, for the D5 power-symbol tests (step 6, B2b).

A supply `PSU` (ports `24`, `0`) and three loads `LA`, `LB`, `LC` (ports `p24`, `p0`, `pe`),
wired as three nets of four, four and three ports: the 24 V net (text `+24`) takes the supply
bar, the 0 V net ground, and the earth net protective earth. On a sheet too narrow for one page
the nets are cut, and each end of a cut is a power end. Nothing here names a real plant.
"""

from decimal import Decimal
from functools import cache
from itertools import pairwise

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.engines.schematic.read.house import DEFAULT_PROFILE
from fransys_model.kernel import Draft, Model, Origin, freeze, make_id
from fransys_model.layout import Profile, SheetFormat
from fransys_model.vocab import (
    Conductor,
    ConductorKind,
    Current,
    Function,
    FunctionKind,
    Item,
    Net,
    NetClass,
    Port,
    PortRole,
    Rail,
    SupplySystem,
)

_ORIGIN = Origin(file="tests/power_fixture.py", line=1, note="D5 power fixture")
_LOADS = ("la", "lb", "lc")


def _port(item: str, name: str) -> Port:
    key = (item, "f", name)
    return Port(
        id=make_id(Port, key),
        key=key,
        function=make_id(Function, (item, "f")),
        template=None,
        name=name,
        role=PortRole.GENERIC,
    )


def _net(key: str, ports: list[Port], *, potential: str | None, name: str | None, pe: bool) -> Net:
    return Net(
        id=make_id(Net, (key,)),
        key=(key,),
        name=name,
        net_class=NetClass.PE if pe else NetClass.GENERIC,
        ports=tuple(sorted(port.id for port in ports)),
        potential=potential,
    )


def power_ports() -> dict[str, Port]:
    """Every port by `item.name`."""
    names = [("psu", "24"), ("psu", "0")] + [
        (load, n) for load in _LOADS for n in ("p24", "p0", "pe")
    ]
    return {f"{item}.{name}": _port(item, name) for item, name in names}


def power_records() -> list:
    """The plant's records: items, functions, ports, the three star nets and a DC supply."""
    ports = power_ports()
    items = ("psu", *_LOADS)
    records: list = [
        Item(
            id=make_id(Item, (i,)),
            key=(i,),
            part=None,
            parent=None,
            position=None,
            tag=i.upper(),
            description="",
            installed=True,
        )
        for i in items
    ]
    records += [
        Function(
            id=make_id(Function, (i, "f")),
            key=(i, "f"),
            item=make_id(Item, (i,)),
            template=None,
            name="f",
            kind=FunctionKind.GENERIC,
        )
        for i in items
    ]
    on_24 = [ports["psu.24"], *(ports[f"{load}.p24"] for load in _LOADS)]
    on_0 = [ports["psu.0"], *(ports[f"{load}.p0"] for load in _LOADS)]
    earth = [ports[f"{load}.pe"] for load in _LOADS]
    key = ("s",)
    rails = {"24V": Rail(max_v=Decimal(24), phase=None), "0V": Rail(max_v=Decimal(0), phase=None)}
    wires = [pair for group in (on_24, on_0, earth) for pair in pairwise(group)]
    records += [
        Conductor(
            id=make_id(Conductor, (f"w{n}",)),
            key=(f"w{n}",),
            a=a.id,
            b=b.id,
            kind=ConductorKind.WIRE,
            carrier=None,
        )
        for n, (a, b) in enumerate(wires)
    ]
    records += [
        *ports.values(),
        _net("rail24", on_24, potential="24V", name="+24", pe=False),
        _net("rail0", on_0, potential="0V", name=None, pe=False),
        _net("earth", earth, potential=None, name=None, pe=True),
        SupplySystem(
            id=make_id(SupplySystem, key),
            key=key,
            name="s",
            current=Current.DC,
            rails=frozendict(rails),
        ),
    ]
    return records


@cache
def power_run() -> tuple:
    """`(model, inputs, results, findings)` of the plant on a 60 mm sheet, built once.

    Four pages and eleven power ends; every test module of the power symbols shares it.
    """
    model = power_model(60)
    inputs = read_inputs(model)
    results, findings = stage_results(model, inputs)
    return model, inputs, results, findings


def power_model(width_mm: int | None = None) -> Model:
    """The plant, frozen; on an authored sheet of `width_mm` of content when given."""
    draft = Draft()
    draft.extend(power_records(), origin=_ORIGIN)
    if width_mm is not None:
        sheet = SheetFormat(
            id=make_id(SheetFormat, ("test", "sheet")),
            key=("test", "sheet"),
            name="narrow",
            width_mm=width_mm + 20,
            height_mm=297,
            content_x_mm=10,
            content_y_mm=10,
            content_width_mm=width_mm,
            content_height_mm=277,
            frame_columns=8,
            frame_rows=6,
            module_mm=Decimal("2.5"),
        )
        profile = Profile(
            id=make_id(Profile, ("test", "profile")),
            key=("test", "profile"),
            sheet_format=sheet.id,
            column_gap=DEFAULT_PROFILE.column_gap,
            row_gap=DEFAULT_PROFILE.row_gap,
            route_margin=DEFAULT_PROFILE.route_margin,
            text_height=DEFAULT_PROFILE.text_height,
            marker_padding=DEFAULT_PROFILE.marker_padding,
            route_turn_penalty=DEFAULT_PROFILE.route_turn_penalty,
            route_crossing_penalty=DEFAULT_PROFILE.route_crossing_penalty,
            band_ranks=DEFAULT_PROFILE.band_ranks,
            group_ranks=DEFAULT_PROFILE.group_ranks,
        )
        draft.extend((sheet, profile), origin=_ORIGIN)
    return freeze(draft)
