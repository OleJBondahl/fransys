"""Fixtures for the wago tests: an invented PLC rack built with the model API.

Every part, MPN and designation here is invented (CLAUDE.md invariant 6); the module MPNs are
public WAGO catalogue numbers of module types. The builder holds
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from library_records import shuffled_draft

from fransys_model.kernel import Draft, Origin, freeze, make_id
from fransys_model.vocab.core import Function, Item
from fransys_model.vocab.enums import FunctionKind, PartCategory, SignalType
from fransys_model.vocab.facets.plc import PlcBindingFacet, PlcChannelFacet, PlcRequestFacet
from fransys_model.vocab.facets.scaling import ScalingFacet
from fransys_model.vocab.templates import FunctionTemplate, Part

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model, Record

_ORIGIN = Origin(file="packages/fransys-wago/tests/conftest.py", line=1, note="invented rack")


@dataclass(frozen=True, slots=True)
class Module:
    """A stamped module: its item and its channel functions in channel order."""

    item: Id[Item]
    channels: tuple[Id[Function], ...]


class Rack:
    """Records of an invented rack: modules under one rack item, and the devices bound to them."""

    def __init__(self, designation: str = "R1") -> None:
        self.records: list[Record] = []
        self._templates: dict[Id[Part], list[Id[FunctionTemplate]]] = {}
        self.rack: Id[Item] = make_id(Item, ("rack",))
        self.records.append(
            Item(
                id=self.rack,
                key=("rack",),
                part=None,
                parent=None,
                position=None,
                tag=designation,
                description="Invented rack",
            )
        )

    def part(  # noqa: PLR0913 -- one keyword per thing a test varies
        self,
        key: str,
        mpn: str,
        signals: tuple[SignalType, ...],
        *,
        description: str | None = None,
        catalogue_description: str | None = None,
        category: PartCategory = PartCategory.PLC_MODULE,
    ) -> Id[Part]:
        """A module part with one channel template per signal, numbered from 1."""
        part = Part(
            id=make_id(Part, (key,)),
            key=(key,),
            mpn=mpn,
            manufacturer="Example Co",
            description=f"Invented {mpn}" if description is None else description,
            category=category,
            class_code="A",
            catalogue_description=catalogue_description,
        )
        self.records.append(part)
        self._templates[part.id] = []
        for number, signal in enumerate(signals, start=1):
            template = FunctionTemplate(
                id=make_id(FunctionTemplate, (key, f"ch{number}")),
                key=(key, f"ch{number}"),
                part=part.id,
                name=f"ch{number}",
                kind=FunctionKind.PLC_CHANNEL,
            )
            facet = PlcChannelFacet(
                id=make_id(PlcChannelFacet, (key, f"ch{number}", "facet")),
                key=(key, f"ch{number}", "facet"),
                subject=template.id,
                signal=signal,
                channel=number,
            )
            self.records.extend([template, facet])
            self._templates[part.id].append(template.id)
        return part.id

    def module(self, part: Id[Part], key: str, designation: str | None, position: int) -> Module:
        """One module of `part` under the rack, with one function per channel template."""
        item = Item(
            id=make_id(Item, (key,)),
            key=(key,),
            part=part,
            parent=self.rack,
            position=position,
            tag=designation,
            description="Invented module",
        )
        self.records.append(item)
        channels = []
        for number, template in enumerate(self._templates[part], start=1):
            function = Function(
                id=make_id(Function, (key, f"ch{number}")),
                key=(key, f"ch{number}"),
                item=item.id,
                template=template,
                name=f"ch{number}",
                kind=FunctionKind.PLC_CHANNEL,
            )
            self.records.append(function)
            channels.append(function.id)
        return Module(item=item.id, channels=tuple(channels))

    def device(  # noqa: PLR0913 -- one keyword per thing a test varies
        self,
        key: str,
        designation: str,
        signal_name: str | None,
        channel: Id[Function],
        *,
        signal: SignalType = SignalType.DI,
        scaling: tuple[str | None, int, int, Decimal, Decimal] | None = None,
        routing: str | None = None,
    ) -> None:
        """A field device bound to `channel`; without a `signal_name` it has no request."""
        item = Item(
            id=make_id(Item, (key,)),
            key=(key,),
            part=None,
            parent=None,
            position=None,
            tag=designation,
            description="Invented field device",
        )
        function = Function(
            id=make_id(Function, (key, "signal")),
            key=(key, "signal"),
            item=item.id,
            template=None,
            name="signal",
            kind=FunctionKind.SENSOR,
        )
        self.records.extend(
            [
                item,
                function,
                PlcBindingFacet(
                    id=make_id(PlcBindingFacet, (key, "binding")),
                    key=(key, "binding"),
                    subject=function.id,
                    channel=channel,
                ),
            ]
        )
        if signal_name is not None:
            self.records.append(
                PlcRequestFacet(
                    id=make_id(PlcRequestFacet, (key, "request")),
                    key=(key, "request"),
                    subject=function.id,
                    signal=signal,
                    signal_name=signal_name,
                    priority=1,
                    routing=routing,
                )
            )
        if scaling is not None:
            unit, raw_min, raw_max, eng_min, eng_max = scaling
            self.records.append(
                ScalingFacet(
                    id=make_id(ScalingFacet, (key, "scaling")),
                    key=(key, "scaling"),
                    subject=function.id,
                    unit=unit,
                    raw_min=raw_min,
                    raw_max=raw_max,
                    eng_min=eng_min,
                    eng_max=eng_max,
                )
            )

    def spare(  # noqa: PLR0913 -- one keyword per setting a test varies
        self,
        key: str,
        channel: Id[Function],
        *,
        name: str | None = None,
        routing: str | None = None,
        configured: bool = True,
        scaling: tuple[str | None, int, int, Decimal, Decimal] | None = None,
    ) -> None:
        """Settings on a spare `channel` itself: its own name, routing, scaling, or `configured=False`."""
        self.records.append(
            PlcRequestFacet(
                id=make_id(PlcRequestFacet, (key, "settings")),
                key=(key, "settings"),
                subject=channel,
                signal=None,
                signal_name=name,
                priority=0,
                routing=routing,
                configured=configured,
            )
        )
        if scaling is not None:
            unit, raw_min, raw_max, eng_min, eng_max = scaling
            self.records.append(
                ScalingFacet(
                    id=make_id(ScalingFacet, (key, "scaling")),
                    key=(key, "scaling"),
                    subject=channel,
                    unit=unit,
                    raw_min=raw_min,
                    raw_max=raw_max,
                    eng_min=eng_min,
                    eng_max=eng_max,
                )
            )

    def draft(self, seed: int | None = None) -> Draft:
        """The records in a `Draft`, shuffled by `seed` when there is one."""
        return shuffled_draft(self.records, _ORIGIN, seed)

    def freeze(self, seed: int | None = None) -> Model:
        """The frozen model of every record so far."""
        return freeze(self.draft(seed))


def build_demo() -> Rack:
    """Rack `R1` of seven modules: a coupler, two digital-in parts, a digital-out, an analog one, a mixed one and a two-kind analog.
    `T1_Level` is scaled 4..20 to 0..100 percent with a routing path, `T2_Flow` has `Routing=""`, the third analog
    channel is a spare named `unused` and scaled; the first digital output is left out (`configured=False`).
    """
    rack = Rack()
    di_text = "16-channel digital input"
    coupler = rack.part("coupler", "750-352", (), description="Invented fieldbus coupler")
    di = rack.part("di", "750-1405", (SignalType.DI,) * 3, description=di_text)
    do = rack.part("do", "750-1504", (SignalType.DO,) * 2, description="4-channel digital output")
    ai = rack.part("ai", "750-455", (SignalType.AI_CURRENT,) * 3, description="4-channel 4-20 mA")
    di_one = rack.part("di1", "750-1405", (SignalType.DI,), description=di_text)
    mixed = rack.part("mix", "750-1506", (SignalType.DI, SignalType.DO, SignalType.DI, SignalType.DO), description="8-channel digital")
    rtd = rack.part(
        "rtd",
        "750-460",
        (SignalType.RTD, SignalType.AI_VOLTAGE),
        description="2-channel Pt100",
        catalogue_description="2-channel analog input; For Pt100/RTD resistance sensors",
    )
    parts = (
        (coupler, "a0", "A0"),
        (di, "a1", "A1"),
        (do, "a2", "A2"),
        (ai, "a3", "A3"),
        (di_one, "a4", "A4"),
        (mixed, "a5", "A5"),
        (rtd, "a6", "A6"),
    )
    mods = [rack.module(part, key, tag, n) for n, (part, key, tag) in enumerate(parts)]
    _, a1, a2, a3, _, a5, _ = mods
    rack.device("m1", "M1", "Start", a5.channels[1], signal=SignalType.DO)
    rack.device("m2", "M2", "Run", a5.channels[3], signal=SignalType.DO)
    rack.device("m3", "M3", "Ready", a5.channels[0])
    rack.device("m4", "M4", "Fault", a5.channels[2])
    rack.spare("a2ch1", a2.channels[0], configured=False)
    rack.device("b1", "B1", "Door", a1.channels[0])
    rack.device("b2", "B2", "Gate", a1.channels[1])
    rack.device("k1", "K1", "Fan", a2.channels[1], signal=SignalType.DO)
    scaling = ("percent", 4, 20, Decimal(0), Decimal(100))
    rack.device("t1", "T1", "Level", a3.channels[0], signal=SignalType.AI_CURRENT, scaling=scaling, routing="Controller.Section.Level")
    rack.device("t2", "T2", "Flow", a3.channels[1], signal=SignalType.AI_CURRENT, routing="")
    rack.spare("a3ch3", a3.channels[2], name="unused", scaling=("percent", 0, 32767, Decimal(0), Decimal(100)))
    return rack


@pytest.fixture
def demo_rack() -> Rack:
    """A fresh copy of the invented rack, for a test that adds to it."""
    return build_demo()


@pytest.fixture
def new_rack() -> type[Rack]:
    """`Rack`, for a test that builds its own."""
    return Rack
