"""Field case: a function with pins 1, 2 and 3 and no pole link pairs (1, 2) and keeps (3).

The engineering shape: a block whose part file states three pins and no pole link, so nothing
says which pins form a pole. Pins 1 and 3 face north, pin 2 south, all wired.

The bug: `series_pairs` and `bundles` saw one pole of all three pins, while the contact table kept
only digit-named pins and the author only marked ones, so an odd pin could vanish.
(A contact function with no link is a lint error, so the contact table is tested in
`packages/fransys-model/tests/derive/test_unlinked_contacts.py`.)
The fix: decision model-0128 and G3 (POLE-04): `unlinked_poles` is the one fallback, every reader
calls it, and an odd pin left over is a one-pin pole, last.
"""

from typing import TYPE_CHECKING

import fransys as fr
import pytest
from fransys.colours import BU

from fransys_model.derive.pole_lists import poles_of
from fransys_model.derive.rows_series_pairs import SeriesPair
from fransys_model.derive.series_pairs import series_pairs
from fransys_model.layout import Side
from fransys_model.vocab.tables import functions, port_templates, ports

if TYPE_CHECKING:
    from pathlib import Path

_PART = (
    'schema = 1\n\n[part]\nmpn = "PLANT-AUX-3"\nmanufacturer = "Plant"\n'
    'description = "Planted contact block"\ncategory = "electromechanical"\nclass_code = "K"\n\n'
    '[[function]]\nname = "aux"\nkind = "generic"\nsymbol = "make-contact"\n'
    "ports = [\n"
    '    { name = "1", role = "generic", symbol_port = "in" },\n'
    '    { name = "2", role = "generic", symbol_port = "out" },\n'
    '    { name = "3", role = "generic", symbol_port = "in" },\n'
    "]\n"
)


@pytest.fixture(scope="module")
def planted(tmp_path_factory: pytest.TempPathFactory, monkeypatch_module) -> fr.Model:
    """One design: the planted block K1 with pins 1 to 3 wired to demo connectors."""
    root: Path = tmp_path_factory.mktemp("planted")
    package = root / "fieldcase_pole_fallback_parts"
    (package / "parts").mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "library.toml").write_text(
        'schema = 1\nname = "fieldcase_pole_fallback_parts"\nversion = "0.1.0"\n'
        'description = "Planted"\n',
        encoding="utf-8",
    )
    (package / "parts" / "aux.toml").write_text(_PART, encoding="utf-8")
    monkeypatch_module.syspath_prepend(str(root))
    d = fr.design("fieldcase_pole_fallback_parts", "demo_parts")
    d.location("L0", "Workshop")
    with d.function("AUX", "Aux block"):
        k = d.device("K1", "PLANT-AUX-3", place="L0")
        for pin, far in ((1, "J1"), (2, "J2"), (3, "J3")):
            d.detail.wire(k[pin], d.device(far, "DEMO-CONN-2P", place="L0")[1], wire=(BU, 0.5))
    return fr.build(d).model


@pytest.fixture(scope="module")
def monkeypatch_module():
    with pytest.MonkeyPatch.context() as mp:
        yield mp


def _aux(model: fr.Model):
    (found,) = [f for f in functions(model).values() if f.name == "aux"]
    return found


def test_the_poles_are_one_two_and_three(planted: fr.Model) -> None:
    aux = _aux(planted)
    own = [p.template for p in ports(planted).values() if p.function == aux.id and p.template]
    names = [
        tuple(port_templates(planted)[t.id].name for t in pole.ends)
        for pole in poles_of(planted, aux.kind, own)
    ]
    assert names == [("1", "2"), ("3", "3")]


def test_series_pairs_pair_pins_one_and_two_only(planted: fr.Model) -> None:
    aux = _aux(planted)
    pin = {p.name: p.id for p in ports(planted).values() if p.function == aux.id}
    sides = {pin["1"]: Side.N, pin["2"]: Side.S, pin["3"]: Side.N}
    assert series_pairs(planted, aux.id, sides) == (
        SeriesPair(pole=0, north=pin["1"], south=pin["2"]),
    )
