"""Field case: a three-pin part that states no pole link, wired pin by pin through the author.

Engineering shape: a planted three-wire sensor on a plug has pins 1 to 3, no `side` and no
internal link. Each pin is wired to its own strip terminal with `d.detail.wire`.

A regression pin, not a reproduced bug: no consumer report and no failing run came first. The
model pairs consecutive pins in marking order and leaves an odd last pin alone: pins 1 and 2 are
one pole, pin 3 has no partner. EL-5 moved that rule into `poles_of_template`, which the author
now reads too; this case holds the built model's pole (1, 2) and no pair that holds 3. The bare
function in a `d.series` stays refused; this case is the wired-by-pin path.

Decision: author-0063 (the author's pole fallback is the part fact).
"""

from typing import TYPE_CHECKING

import fransys as fr
from fransys.colours import BK

from fransys_model.derive import series_pairs
from fransys_model.derive.rows_series_pairs import SeriesPair
from fransys_model.layout import Side

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

    from fransys_model.kernel import Id
    from fransys_model.vocab.core import Function, Port

_PART = (
    'schema = 1\n\n[part]\nmpn = "PLANT-SENS-3P"\nmanufacturer = "Plant"\n'
    'description = "Planted three-pin sensor, no pole link"\ncategory = "generic"\n'
    'class_code = "B"\n\n[[function]]\nname = "sig"\nkind = "sensor"\n'
    "ports = [\n"
    '    { name = "1", role = "generic" },\n'
    '    { name = "2", role = "generic" },\n'
    '    { name = "3", role = "generic" },\n'
    "]\n"
)


def _model(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[fr.Model, Id[Function], dict[str, Id[Port]]]:
    """The built model, the sensor's function and its pins by name."""
    package = root / "fieldcase_three_pin_parts"
    (package / "parts").mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "library.toml").write_text(
        'schema = 1\nname = "fieldcase_three_pin_parts"\nversion = "0.1.0"\n'
        'description = "Planted"\n',
        encoding="utf-8",
    )
    (package / "parts" / "sensor3p.toml").write_text(_PART, encoding="utf-8")
    monkeypatch.syspath_prepend(str(root))
    d = fr.design("fieldcase_three_pin_parts", "demo_parts", place="CAB")
    strip = d.terminal_strip("X1", "DEMO-TB-2.5", 4)
    sensor = d.device("B1", "PLANT-SENS-3P")
    for n in (1, 2, 3):
        d.detail.wire(strip[n], sensor.sig[str(n)], wire=(BK, 0.75))
    model = fr.build(d).model
    function = next(f for f in fr.derive.functions(model).values() if f.name == "sig")
    pins = {p.name: p.id for p in fr.derive.ports(model).values() if p.function == function.id}
    return model, function.id, pins


def test_pins_1_and_2_are_a_pole_and_pin_3_pairs_with_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model, function, ids = _model(tmp_path, monkeypatch)
    ends = {ids["1"]: Side.N, ids["2"]: Side.S}
    assert series_pairs(model, function, ends) == (
        SeriesPair(pole=0, north=ids["1"], south=ids["2"]),
    )
    across = {ids["1"]: Side.N, ids["3"]: Side.S}
    assert series_pairs(model, function, across) == ()
