"""EF-B2 spec test: a switch or protection part with no `symbol` draws the symbol its facts name.

The engineering shape: a stop push button (one break contact, closed at rest) whose part names
no `symbol`, an emergency stop that names `emergency-stop`, and a fuse, a miniature circuit
breaker and an overload relay as protection parts that name no `symbol`, each wired between two
terminals.

The bug: with no authored symbol every switch drew the one default of its kind and every
protection a circuit breaker, whatever the rest state or the device type said.

The rule (decision layout-0105, spec electrical-facts F2, F3): a switch follows the rest state of
its switched links (closed at rest draws `break-contact`), a protection follows its type (`fuse`,
`circuit-breaker`, `thermal-overload`), and a symbol the part names still wins.
"""

from pathlib import Path

import fransys as fr
import fransys_author.surface as author_surface
import fransys_parts
import pytest
from fransys.colours import BU

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_model.vocab.tables import functions, items

_LIBRARY = 'schema = 1\nname = "default-parts"\nversion = "0.1.0"\ndescription = "Invented."\n'
_DEMO_TERMINAL = (
    Path(__file__).parents[3]
    / "examples"
    / "demo-parts"
    / "demo_parts"
    / "parts"
    / "terminal-feedthrough-2_5.toml"
)
_SWITCH = """schema = 1

[part]
mpn = "{mpn}"
manufacturer = "Demo"
description = "Push button, one break contact"
category = "electromechanical"
class_code = "S"

[[function]]
name = "sw"
kind = "switch"
{symbol}ports = [
    {{ name = "A", role = "generic" }},
    {{ name = "B", role = "generic" }},
]
links = [{{ a = "A", b = "B", kind = "switched", rest = "closed" }}]
"""
_PROTECTION = """schema = 1

[part]
mpn = "{mpn}"
manufacturer = "Demo"
description = "Protection device"
category = "protection"
class_code = "F"

[[function]]
name = "element"
kind = "protection"
ports = [
    {{ name = "1", role = "generic" }},
    {{ name = "2", role = "generic" }},
]
links = [{{ a = "1", b = "2", kind = "conductive" }}]

[function.protection]
type = "{kind}"
"""
_CASES = {
    "PB": "break-contact",
    "ES": "emergency-stop",
    "FU": "fuse",
    "MB": "circuit-breaker",
    "OL": "thermal-overload",
}


def _built(tmp_path):
    """Five devices of the shape above, each wired to two terminals of one strip."""
    (tmp_path / "library.toml").write_text(_LIBRARY, encoding="utf-8")
    (tmp_path / "parts").mkdir()
    texts = {
        "terminal": _DEMO_TERMINAL.read_text(encoding="utf-8"),
        "pb": _SWITCH.format(mpn="DEF-PB", symbol=""),
        "es": _SWITCH.format(mpn="DEF-ES", symbol='symbol = "emergency-stop"\n'),
        "fu": _PROTECTION.format(mpn="DEF-FU", kind="fuse"),
        "mb": _PROTECTION.format(mpn="DEF-MB", kind="mcb"),
        "ol": _PROTECTION.format(mpn="DEF-OL", kind="overload"),
    }
    for name, text in texts.items():
        (tmp_path / "parts" / f"{name}.toml").write_text(text, encoding="utf-8")
    parts = fransys_parts.load_path(tmp_path)
    d = author_surface.design(parts, place="C1")
    d.project(title="Defaults", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-02", text="First issue", created="XX")
    cab = d.location("C1", "Cabinet")
    with d.function("CTL", "Control"):
        strip = d.terminal_strip("X1", "DEMO-TB-2.5", 2 * len(_CASES))
        number = 0
        for tag in _CASES:
            device = d.device(tag, f"DEF-{tag}")
            fn = device.sw if tag in {"PB", "ES"} else device.element
            for pin in ("A", "B") if tag in {"PB", "ES"} else ("1", "2"):
                number += 1
                d.wire(strip[number], fn[pin], wire=(BU, 0.5))
    cover = tmp_path / "cabinet.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    return fr.build(d, doc).model


@pytest.fixture(scope="module")
def drawn(tmp_path_factory) -> dict[str | None, str]:
    """The symbol each device's function draws, by its item tag."""
    model = _built(tmp_path_factory.mktemp("defaults"))
    results, _ = stage_results(model, read_inputs(model))
    tag_of = {f.id: items(model)[f.item].tag for f in functions(model).values()}
    return {tag_of[p.function]: p.geometry.key for p in results.layout.placed}


@pytest.mark.parametrize(("tag", "symbol"), _CASES.items())
def test_a_device_draws_the_symbol_its_facts_name(drawn, tag: str, symbol: str) -> None:
    assert drawn[tag] == symbol
