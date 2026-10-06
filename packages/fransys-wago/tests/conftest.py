"""Fixtures for the wago tests: an invented PLC rack built with the model API.

Every part, MPN and designation here is invented (CLAUDE.md invariant 6); the module MPNs are
public WAGO catalogue numbers of module types, which the work order allows. The builder holds
records, not a frozen model, so a test can reorder them before they reach a `Draft`.
"""

import random
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest

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

    def part(
        self,
        key: str,
        mpn: str,
        signals: tuple[SignalType, ...],
        *,
        description: str | None = None,
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
        scaling: tuple[str, int, int, Decimal, Decimal] | None = None,
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

    def draft(self, seed: int | None = None) -> Draft:
        """The records in a `Draft`, shuffled by `seed` when there is one."""
        records = list(self.records)
        if seed is not None:
            random.Random(seed).shuffle(records)  # noqa: S311 -- a test shuffle, not security
        draft = Draft()
        draft.extend(records, origin=_ORIGIN)
        return draft

    def freeze(self, seed: int | None = None) -> Model:
        """The frozen model of every record so far."""
        return freeze(self.draft(seed))


def build_demo() -> Rack:
    """Rack `R1` of five modules: a coupler, two of one digital-in part, a digital-out, an analog.

    - `A0`, position 0: the coupler `750-352`, no channels (not emitted).
    - `A1`, position 1: `750-1405`, three DI channels, two bound (`B1_Door`, `B2_Gate`), one spare.
    - `A2`, position 2: `750-1504`, two DO channels, one bound (`K1_Fan`), one spare.
    - `A3`, position 3: `750-455`, three AI_CURRENT channels: `T1_Level` scaled 4..20 to 0..100
      percent, `T2_Flow` bound without scaling, and one spare.
    - `A4`, position 4: a second `750-1405` (letter `b`), one DI channel, spare.
    """
    rack = Rack()
    coupler = rack.part("coupler", "750-352", (), description="Invented fieldbus coupler")
    di = rack.part("di", "750-1405", (SignalType.DI,) * 3, description="16-channel digital input")
    do = rack.part("do", "750-1504", (SignalType.DO,) * 2, description="4-channel digital output")
    ai = rack.part("ai", "750-455", (SignalType.AI_CURRENT,) * 3, description="4-channel 4-20 mA")
    di_one = rack.part("di1", "750-1405", (SignalType.DI,), description="16-channel digital input")
    rack.module(coupler, "a0", "A0", 0)
    a1 = rack.module(di, "a1", "A1", 1)
    a2 = rack.module(do, "a2", "A2", 2)
    a3 = rack.module(ai, "a3", "A3", 3)
    rack.module(di_one, "a4", "A4", 4)
    rack.device("b1", "B1", "Door", a1.channels[0])
    rack.device("b2", "B2", "Gate", a1.channels[1])
    rack.device("k1", "K1", "Fan", a2.channels[0], signal=SignalType.DO)
    rack.device(
        "t1",
        "T1",
        "Level",
        a3.channels[0],
        signal=SignalType.AI_CURRENT,
        scaling=("percent", 4, 20, Decimal(0), Decimal(100)),
    )
    rack.device("t2", "T2", "Flow", a3.channels[1], signal=SignalType.AI_CURRENT)
    return rack


@pytest.fixture
def demo_rack() -> Rack:
    """A fresh copy of the invented rack, for a test that adds to it."""
    return build_demo()


@pytest.fixture
def new_rack() -> type[Rack]:
    """`Rack`, for a test that builds its own."""
    return Rack
