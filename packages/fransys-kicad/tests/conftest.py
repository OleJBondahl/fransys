"""Fixtures for the kicad tests: an invented board built with the model API, and a reader.

Every part, MPN and designation here is invented (CLAUDE.md invariant 6). The builder holds
records, not a frozen model, so a test can reorder them before they reach a `Draft`.
"""

import random
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

from fransys_model.kernel import Draft, Origin, evolve, freeze, make_id
from fransys_model.vocab import PartBundle, instantiate
from fransys_model.vocab.connectivity import Net
from fransys_model.vocab.core import Function, Item, Port
from fransys_model.vocab.enums import FunctionKind, NetClass, PartCategory, PortRole
from fransys_model.vocab.facets.pcb import FootprintFacet, PcbFacet
from fransys_model.vocab.templates import FunctionTemplate, Part, PortTemplate

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model, Record

_ORIGIN = Origin(file="packages/fransys-kicad/tests/conftest.py", line=1, note="invented board")


@dataclass(frozen=True, slots=True)
class Placed:
    """A stamped item: its id and its ports by `(function, pin)`."""

    item: Id[Item]
    ports: dict[tuple[str, str], Id[Port]]

    def pin(self, pin: str, function: str = "main") -> Id[Port]:
        """The port called `pin` of the function called `function`."""
        return self.ports[function, pin]


class Design:
    """Records of an invented design, added one part, item and net at a time."""

    def __init__(self) -> None:
        self.records: list[Record] = []

    def part(  # noqa: PLR0913 -- one keyword per thing a test varies
        self,
        key: str,
        mpn: str,
        letter: str,
        functions: dict[str, tuple[str, ...]] | None = None,
        *,
        footprint: tuple[str, str] | None = None,
        board: bool = False,
    ) -> PartBundle:
        """A part with one function template per entry of `functions` (name to pin names)."""
        part = Part(
            id=make_id(Part, (key,)),
            key=(key,),
            mpn=mpn,
            manufacturer="Example Co",
            description=f"Invented {mpn}",
            category=PartCategory.BOARD if board else PartCategory.GENERIC,
            class_code=letter,
        )
        function_templates = []
        port_templates = []
        for name, pins in (functions or {}).items():
            template = FunctionTemplate(
                id=make_id(FunctionTemplate, (key, name)),
                key=(key, name),
                part=part.id,
                name=name,
                kind=FunctionKind.GENERIC,
            )
            function_templates.append(template)
            port_templates.extend(
                PortTemplate(
                    id=make_id(PortTemplate, (key, name, pin)),
                    key=(key, name, pin),
                    function=template.id,
                    name=pin,
                    role=PortRole.GENERIC,
                )
                for pin in pins
            )
        self.records.extend([part, *function_templates, *port_templates])
        if board:
            self.records.append(
                PcbFacet(
                    id=make_id(PcbFacet, (key, "pcb")),
                    key=(key, "pcb"),
                    subject=part.id,
                    revision="A",
                )
            )
        if footprint is not None:
            library, name = footprint
            self.records.append(
                FootprintFacet(
                    id=make_id(FootprintFacet, (key, "footprint")),
                    key=(key, "footprint"),
                    subject=part.id,
                    library=library,
                    name=name,
                )
            )
        return PartBundle(
            part=part,
            function_templates=tuple(function_templates),
            port_templates=tuple(port_templates),
            internal_links=(),
        )

    def item(
        self,
        bundle: PartBundle,
        key: str,
        designation: str | None,
        *,
        parent: Placed | None = None,
        installed: bool = True,
    ) -> Placed:
        """One item of `bundle`'s part, under `parent`."""
        stamped = instantiate(
            bundle,
            (key,),
            tag=designation,
            parent=None if parent is None else parent.item,
            description=bundle.part.description,
            installed=installed,
        )
        self.records.extend(stamped)
        function_names = {r.id: r.name for r in stamped if isinstance(r, Function)}
        return Placed(
            item=next(r.id for r in stamped if isinstance(r, Item)),
            ports={
                (function_names[r.function], r.name): r.id for r in stamped if isinstance(r, Port)
            },
        )

    def net(self, key: str, ports: tuple[Id[Port], ...], *, name: str | None = None) -> None:
        """A declared net called `name`, or named by its key when `name` is `None`."""
        self.records.append(
            Net(
                id=make_id(Net, (key,)),
                key=(key,),
                name=name,
                net_class=NetClass.GENERIC,
                ports=ports,
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


@dataclass(frozen=True, slots=True)
class Demo:
    """The invented board of `demo_board`: its design, ids and the header pin left open."""

    design: Design
    resistor_part: PartBundle
    board: Placed
    resistor_1: Placed
    resistor_2: Placed
    header: Placed
    standoff: Placed

    def freeze(self, seed: int | None = None) -> Model:
        """The frozen model."""
        return self.design.freeze(seed)


def build_demo() -> Demo:
    """Board `JB1` with two resistors, a 4-pin header and a standoff without a footprint.

    Nets `VCC`, `SIG` and `GND` join every pin but header pin 4, which is left open.
    """
    design = Design()
    board_part = design.part("board", "SIM-BOARD-DEMO", "A", board=True)
    resistor = design.part(
        "resistor",
        "SIM-R-0603",
        "R",
        {"main": ("1", "2")},
        footprint=("Resistor_SMD", "R_0603_1608Metric"),
    )
    header = design.part(
        "header",
        "SIM-HDR-4P",
        "J",
        {"main": ("1", "2", "3", "4")},
        footprint=("Connector_PinHeader_2.54mm", "PinHeader_1x04_P2.54mm_Vertical"),
    )
    standoff = design.part("standoff", "SIM-STANDOFF-M3", "H")
    board = design.item(board_part, "jb1", "JB1")
    r1 = design.item(resistor, "jb1-r1", "R1", parent=board)
    r2 = design.item(resistor, "jb1-r2", "R2", parent=board)
    j1 = design.item(header, "jb1-j1", "J1", parent=board)
    h1 = design.item(standoff, "jb1-h1", "H1", parent=board)
    design.net("vcc", (j1.pin("1"), r1.pin("1")), name="VCC")
    design.net("sig", (r1.pin("2"), r2.pin("1"), j1.pin("2")), name="SIG")
    design.net("gnd", (r2.pin("2"), j1.pin("3")), name="GND")
    return Demo(
        design=design,
        resistor_part=resistor,
        board=board,
        resistor_1=r1,
        resistor_2=r2,
        header=j1,
        standoff=h1,
    )


@pytest.fixture
def demo_board() -> Demo:
    """A fresh copy of the invented board, for a test that adds to it."""
    return build_demo()


@pytest.fixture
def edit():
    """A function that replaces one record of a frozen model by an edited copy of it."""

    def replace(model: Model, record: Record) -> Model:
        return evolve(model, remove=(record.id,), put=(record,), origin=_ORIGIN)

    return replace


@pytest.fixture
def new_design() -> type[Design]:
    """`Design`, for a test that builds its own board."""
    return Design


_TOKEN = re.compile(
    r'\s*(?:(?P<open>\()|(?P<close>\))|"(?P<string>(?:[^"\\]|\\.)*)"|(?P<atom>[^\s()"]+))'
)
_ESCAPES = {"n": "\n", "r": "\r"}


def _unescape(text: str) -> str:
    return re.sub(r"\\(.)", lambda match: _ESCAPES.get(match[1], match[1]), text)


def _tokens(text: str) -> list[tuple[str, str]]:
    """`(kind, text)` for every token: `open`, `close`, `string` (still escaped) or `atom`."""
    found = []
    position = 0
    text = text.rstrip()
    while position < len(text):
        match = _TOKEN.match(text, position)
        if match is None or match.lastgroup is None:
            msg = f"cannot read a token at offset {position}"
            raise ValueError(msg)
        found.append((match.lastgroup, match[match.lastgroup]))
        position = match.end()
    return found


def _read(tokens: list[tuple[str, str]], start: int) -> tuple[list, int]:
    """The list whose opening parenthesis is `tokens[start]`, and the index after its closing."""
    if start >= len(tokens) or tokens[start][0] != "open":
        msg = "expected an opening parenthesis"
        raise ValueError(msg)
    node: list = []
    position = start + 1
    while position < len(tokens):
        kind, text = tokens[position]
        if kind == "close":
            return node, position + 1
        if kind == "open":
            child, position = _read(tokens, position)
            node.append(child)
        else:
            node.append(_unescape(text) if kind == "string" else text)
            position += 1
    msg = "an unclosed parenthesis"
    raise ValueError(msg)


def parse_sexpr(text: str) -> list:
    """Read one s-expression into nested lists of `str`, the way KiCad's lexer reads a netlist.

    A quoted string and a bare atom both become a `str`; only the parentheses make a list.

    Raises:
        ValueError: the text is not exactly one balanced expression.
    """
    tokens = _tokens(text)
    node, end = _read(tokens, 0)
    if end != len(tokens):
        msg = "text after the top-level expression"
        raise ValueError(msg)
    return node


@pytest.fixture
def sexpr():
    """`parse_sexpr`, for a test that reads a netlist back."""
    return parse_sexpr
