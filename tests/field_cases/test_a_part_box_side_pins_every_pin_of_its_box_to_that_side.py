"""Field case: a small signal box draws its pins half over half; a part may pin every pin of a function to one side (BOX-SIDES, designer R2060).
A part's `box_side = "top"` puts every drawn pin of the box on N, `"bottom"` on S; another value is an ENUM_VALUE error naming the function."""

from pathlib import Path

import fransys as fr
import pytest
from _drawn_facts import item_box
from _model_build_cover import unit_document
from fransys.colours import BU

DATA = Path(__file__).parent / "data"
_PINS = ("p1", "p2", "p3", "p4")


def _model(part: str) -> fr.Model:
    d = fr.design("box_side_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    strip = d.terminal_strip("X1", "BOX-TB", 4).run("L", 4)
    with d.function("G", "Group"):
        box = d.device("U1", part)
        for n, pin in enumerate(_PINS, start=1):
            d.series(strip[n].outer, box[pin], wire=(BU, 0.5))
    return fr.build(d, unit_document(cab)).model


@pytest.fixture(scope="module", autouse=True)
def _library():
    with pytest.MonkeyPatch.context() as mp:
        mp.syspath_prepend(str(DATA))
        yield


@pytest.mark.parametrize(("part", "side"), [("BOX-TOP", "n"), ("BOX-BOTTOM", "s")])
def test_every_pin_of_a_pinned_box_is_on_its_side(part: str, side: str) -> None:
    sides = item_box(_model(part), "U1").sides
    assert {sides[pin] for pin in _PINS} == {side}
    assert len(sides) == len(_PINS)


_FUNCTION = '[[function]]\nname = "{name}"\nkind = "{kind}"\nbox_side = "{side}"\nports = [{ports}]\n'
_KINDS = ("load", "sensor", "load")  # ranks differ, so the rank split would apply
_PART = 'schema = 2\n\n[part]\nmpn = "{mpn}"\nmanufacturer = "Demo"\ndescription = "Generated"\ncategory = "generic"\nclass_code = "B"\n\n'


def _library(root: Path, functions: int, side: str) -> str:
    """A part of `functions` functions of two pins each, every one pinned to `side`; returns its mpn."""
    lib = root / f"gen_box_parts_{functions}{side}"
    (lib / "parts").mkdir(parents=True, exist_ok=True)
    (lib / "__init__.py").write_text("", encoding="utf-8")
    (lib / "library.toml").write_text(
        f'schema = 2\nname = "gen-box-parts-{functions}{side}"\nversion = "0.1.0"\ndescription = "Generated."\n', encoding="utf-8"
    )
    mpn = f"GEN-{functions}F-{side.upper()}"
    body = "".join(
        _FUNCTION.format(name=f"f{f}", kind=_KINDS[f], side=side, ports=", ".join(f'{{ name = "{c}{f}", role = "generic" }}' for c in "ab"))
        for f in range(functions)
    )
    (lib / "parts" / f"{mpn}.toml").write_text(_PART.format(mpn=mpn) + body, encoding="utf-8")
    return mpn


@pytest.mark.rule("BOX-SIDES")
@pytest.mark.parametrize("side", ["top", "bottom"])
@pytest.mark.parametrize("functions", [1, 2, 3])
def test_every_pin_of_every_function_of_a_pinned_box_is_on_its_side(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, functions: int, side: str
) -> None:
    mpn = _library(tmp_path, functions, side)
    monkeypatch.syspath_prepend(str(tmp_path))
    d = fr.design(f"gen_box_parts_{functions}{side}", "box_side_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    strip = d.terminal_strip("X1", "BOX-TB", 2 * functions).run("L", 2 * functions)
    with d.function("G", "Group"):
        box = d.device("U1", mpn)
        pins = [box[f"{c}{f}"] for f in range(functions) for c in "ab"]
        for n, pin in enumerate(pins, start=1):
            d.series(strip[n].outer, pin, wire=(BU, 0.5))
    sides = item_box(fr.build(d, unit_document(cab)).model, "U1").sides
    assert len(sides) == 2 * functions
    assert set(sides.values()) == {"n" if side == "top" else "s"}
