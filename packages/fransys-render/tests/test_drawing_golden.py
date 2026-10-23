"""A planted page's `Drawing` JSON is pinned: the value a writer must produce (layout-0315)."""

import json
from pathlib import Path

from fransys_el import style
from fransys_render.draw import svg

from electrical_symbols import LIBRARY
from fransys_layout.core import Size, from_plain, to_plain
from fransys_layout.drawing import Drawing, DrawnSymbol, DrawnWire

STYLE = style(LIBRARY)
_GOLDEN = Path(__file__).parent / "golden" / "drawings" / "planted_page.json"
PLANTED = Drawing(
    area=Size(800, 400),
    symbols=(
        DrawnSymbol("s1", "break-contact", 80, 16, "R0", slots=(("tag", "-K1"),)),
        DrawnSymbol(
            "s2",
            "card",
            160,
            16,
            "MR90",
            stretch=(("x", 320),),
            offsets=(("c1", 48), ("c2", 112)),
            leads=("c1", "c2"),
            muted=True,
        ),
    ),
    wires=(DrawnWire("w1", ((0, 0), (80, 0), (80, 48)), "wire"),),
    markers=(),
    texts=(),
    outlines=(),
    library_version="planted",
)


def _text() -> str:
    return json.dumps(to_plain(PLANTED), indent=1, sort_keys=True) + "\n"


def test_the_planted_drawing_matches_its_golden():
    assert _text() == _GOLDEN.read_text(encoding="utf-8")


def test_the_golden_reads_back_and_draws():
    read = from_plain(Drawing, json.loads(_GOLDEN.read_text(encoding="utf-8")))
    assert read == PLANTED
    assert svg(read, LIBRARY, STYLE) == svg(PLANTED, LIBRARY, STYLE)


if __name__ == "__main__":  # `just regen-goldens render`
    _GOLDEN.parent.mkdir(parents=True, exist_ok=True)
    _GOLDEN.write_text(_text(), encoding="utf-8", newline="\n")
