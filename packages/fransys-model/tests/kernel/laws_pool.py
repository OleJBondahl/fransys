"""Strategies for `test_laws.py`: one drawn `Pool` of valid records from the demo-parts vocabulary.

The model package imports no workspace package, so `fransys_parts.load("demo_parts")` is out of
reach; the same vocabulary (a relay-like part with a library, templates and a connector facet, a
terminal part, units, nested items, wiring, analog scaling) is built here from invented data.
Text fields and `ext` values also draw unicode, quotes, backslashes and negative or large ints, so
the round trip and the digest see serialization edge cases (keys and ids stay plain ASCII).
"""

import dataclasses
import string
from typing import Any

from hypothesis import strategies as st

from fransys_model.kernel import Id, make_id
from fransys_model.vocab.connectivity import Conductor, Mate, Net
from fransys_model.vocab.core import Function, Item, Port, Unit, UnitRelease
from fransys_model.vocab.enums import (
    ConductorKind,
    FunctionKind,
    Gender,
    LinkKind,
    NetClass,
    PartCategory,
    PortRole,
)
from fransys_model.vocab.facets import ConnectorFacet, ScalingFacet, SupplyFacet, TerminalFacet
from fransys_model.vocab.templates import (
    FunctionTemplate,
    InternalLink,
    Part,
    PartLibrary,
    PortTemplate,
)
from fransys_model.vocab.units import Boundary, UnusedBoundary

_TRICKY = ('"', "\\", 'a"b\\c', "'\n\t", "é ∑ 日本", chr(0x2028), "{}[]:,")
_TEXT = st.text(max_size=8) | st.sampled_from(_TRICKY)
_INTS = st.integers(-(2**63), 2**63) | st.sampled_from((0, -1, 10**30, -(10**30)))
_DESIGNATION = st.none() | st.text(string.ascii_uppercase, min_size=1, max_size=3)
_MARKING = st.sampled_from((None, "", "7"))
_EXT_TAGS = ("none", "note", "mixed", "map", "self", "ints")


@dataclasses.dataclass(frozen=True)
class Pool:
    """One drawn set of valid records, and the aliases that go with them."""

    records: tuple[Any, ...]
    aliases: tuple[tuple[Id[Any], Id[Any]], ...]


class _Plant:
    """Draws one plant; every record it makes lands in `records`, each with a drawn `ext`."""

    def __init__(self, draw: st.DrawFn) -> None:
        self.draw = draw
        self.records: list[Any] = []

    def ext(self, rid: Id[Any]) -> Any:
        """One of a few `ext` shapes: empty, text, scalars, nested maps and tuples, an `Id`."""
        tag = self.draw(st.sampled_from(_EXT_TAGS))
        if tag == "note":
            return frozendict({"note": self.draw(_TEXT)})
        if tag == "mixed":
            return frozendict({"n": 3, "on": True, "nothing": None, "t": ("x", 1)})
        if tag == "map":
            return frozendict({"m": frozendict({"k": ("x", frozendict({"z": 1}))})})
        if tag == "self":
            return frozendict({"ref": rid})
        if tag == "ints":
            return frozendict({"big": self.draw(_INTS), "t": (self.draw(_INTS), self.draw(_TEXT))})
        return frozendict()

    def mk(self, cls: type, *key: str, **fields: Any) -> Any:
        rid = make_id(cls, key)
        made = cls(id=rid, key=key, ext=self.ext(rid), **fields)
        self.records.append(made)
        return made

    def one[T](self, options: Any) -> T:
        return self.draw(st.sampled_from(tuple(options)))

    def type_level(self) -> tuple[Any, Any, Any]:
        """A library (maybe), a relay part, a terminal part, one template with two pins."""
        library = self.mk(PartLibrary, "lib", name="demo-parts", version="0.1.0")
        if not self.draw(st.booleans()):
            self.records.pop()
            library = None
        relay = self.mk(
            Part,
            "relay",
            mpn="DEMO-RLY",
            manufacturer="Demo",
            description=self.draw(_TEXT),
            category=PartCategory.ELECTROMECHANICAL,
            class_code="K",
            library=None if library is None else library.id,
        )
        strip = self.mk(
            Part,
            "term",
            mpn="DEMO-TRM",
            manufacturer="Demo",
            description="Invented terminal",
            category=PartCategory.TERMINAL,
            class_code="X",
            library=None,
        )
        for number in range(self.draw(st.integers(0, 2))):
            self.mk(
                SupplyFacet,
                "relay",
                f"s{number}",
                subject=relay.id,
                supplier="Invented",
                supplier_part_number=f"S-{number}",
                note=self.draw(_TEXT),
            )
        template = self.mk(
            FunctionTemplate, "relay", "coil", part=relay.id, name="coil", kind=FunctionKind.COIL
        )
        pins = [
            self.mk(
                PortTemplate,
                "relay",
                "coil",
                name,
                function=template.id,
                name=name,
                role=PortRole.GENERIC,
                marking=self.draw(_MARKING),
            )
            for name in ("A1", "A2")
        ]
        link_kind = self.one(LinkKind)
        self.mk(InternalLink, "relay", "link", a=pins[0].id, b=pins[1].id, kind=link_kind)
        if self.draw(st.booleans()):
            self.mk(
                ConnectorFacet,
                "relay",
                "conn",
                subject=template.id,
                style="JST-XH",
                pincount=2,
                gender=self.one(Gender),
                marking=self.draw(_MARKING),
            )
        return relay, strip, template

    def units(self) -> list[Any]:
        """Zero to three units, each maybe the child of the one before (a nested `parent`)."""
        units: list[Any] = []
        count = self.draw(st.integers(0, 3))
        release: Any = None
        if count:  # every unit is an instance of the one release `demo-board` 1.<revision>
            revision = self.draw(st.integers(min_value=1, max_value=2**63))
            release = self.mk(
                UnitRelease,
                "unit_release",
                "demo-board",
                "1",
                str(revision),
                name="demo-board",
                version=1,
                revision=revision,
                interface="1",
                title=self.draw(_TEXT),
                number="",
            )
        for number in range(count):
            parent = units[-1].id if units and self.draw(st.booleans()) else None
            units.append(self.mk(Unit, f"u{number}", release=release.id, parent=parent))
        return units

    def item(self, number: int, parts: tuple[Any, Any, Any], others: dict[str, list[Any]]) -> None:
        """One item of a random part, with a function, two ports and maybe facets."""
        relay, strip, template = parts
        part = self.one((relay, strip, None))
        items, units = others["items"], others["units"]
        item = self.mk(
            Item,
            f"i{number}",
            part=None if part is None else part.id,
            parent=items[-1].id if items and self.draw(st.booleans()) else None,
            position=self.draw(st.none() | _INTS),
            tag=self.draw(_DESIGNATION),
            description=self.draw(_TEXT),
            installed=self.draw(st.booleans()),
            unit=self.one((None, *(unit.id for unit in units))),
            external=self.draw(st.booleans()),
        )
        items.append(item)
        function = self.mk(
            Function,
            f"i{number}",
            "f",
            item=item.id,
            template=template.id if part is relay and self.draw(st.booleans()) else None,
            name="f",
            kind=self.one(FunctionKind),
        )
        others["functions"].append(function)
        for pin in ("1", "2"):
            port = self.mk(
                Port,
                f"i{number}",
                "f",
                pin,
                function=function.id,
                template=None,
                name=pin,
                role=self.one(PortRole),
                marking=self.draw(_MARKING),
            )
            others["ports"].append(port)
        if part is strip and self.draw(st.booleans()):
            index = self.draw(_INTS)
            self.mk(TerminalFacet, f"i{number}", "t", subject=item.id, group="L1", index=index)
        if self.draw(st.booleans()):
            self.mk(
                ScalingFacet,
                f"i{number}",
                "s",
                subject=function.id,
                unit=self.draw(_TEXT),
                raw_min=self.draw(_INTS),
                raw_max=self.draw(_INTS),
                eng_min=self.draw(st.decimals(-(10**18), 10**18, places=6)),
                eng_max=self.draw(st.decimals(-999, 999, places=2)),
            )

    def wiring(self, units: list[Any], functions: list[Any], ports: list[Any]) -> None:
        """Conductors, a net, a mate, a boundary and an unused boundary, each maybe."""
        two_ports = st.tuples(st.sampled_from(ports), st.sampled_from(ports))
        for number in range(self.draw(st.integers(0, 3))):
            a, b = self.draw(two_ports.filter(lambda pair: pair[0] != pair[1]))
            kind = self.one(ConductorKind)
            self.mk(Conductor, "w", str(number), a=a.id, b=b.id, kind=kind, carrier=None)
        members = self.draw(st.lists(st.sampled_from(ports), min_size=2, max_size=4, unique=True))
        if self.draw(st.booleans()):
            self.mk(
                Net,
                "net",
                name=self.one((None, "N")),
                net_class=self.one(NetClass),
                ports=tuple(port.id for port in members),
                potential=None,
            )
        first, second = self.draw(
            st.lists(st.sampled_from(functions), min_size=2, max_size=2, unique=True)
        )
        if self.draw(st.booleans()):
            self.mk(Mate, "mate", a=first.id, b=second.id)
        if units and self.draw(st.booleans()):
            self.mk(Boundary, "boundary", unit=self.one(units).id, function=first.id)
        if self.draw(st.booleans()):
            self.mk(UnusedBoundary, "unused", function=second.id)


@st.composite
def pools(draw: st.DrawFn) -> Pool:
    """A valid plant: 2 to 4 items (some nested, some in units), wired, with facets and an alias."""
    plant = _Plant(draw)
    parts = plant.type_level()
    others: dict[str, list[Any]] = {
        "units": plant.units(),
        "items": [],
        "functions": [],
        "ports": [],
    }
    for number in range(draw(st.integers(2, 4))):
        plant.item(number, parts, others)
    plant.wiring(others["units"], others["functions"], others["ports"])
    retired = (make_id(Port, ("retired",)), others["ports"][0].id)
    return Pool(tuple(plant.records), (retired,) if draw(st.booleans()) else ())
