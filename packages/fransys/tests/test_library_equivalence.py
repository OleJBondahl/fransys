"""The module `LIBRARY` and the build's library agree on what class (ii) reads (ES-LIBRARY L3).

Class (ii) of es-0074: `G_PER_MODULE`, `WIRING_GRID`, `PORT_PITCH_G`, `box_pitch`,
`generic_box`, `sized`, `frame_border`, `frame_strip`, `title_block`, `title_logo`,
`notice_table`, `bridge_mark`, `bridge_mark_room`, `natural`, `TITLE_BLOCK_MIN_BAND_MM` and
`TITLE_BLOCK_MIN_WIDTH_MM`. Each reads a symbol by key or a fixed grid field of
`electrical_symbols.LIBRARY`. Under a consumer setting with another font and another
`module_mm`, the library `build_library` makes must give the same symbols and fixed grid
fields, and the body and keep-out boxes must not depend on the font.
"""

from pathlib import Path
from typing import TYPE_CHECKING, cast

import fransys as fr
import pytest
from fransys._settings_library import build_library
from symdef import body_box, keepout_box

from electrical_symbols import G_PER_MODULE, LIBRARY, PORT_PITCH_G, WIRING_GRID
from electrical_symbols.box_ports import PORT_PITCH

if TYPE_CHECKING:
    from collections.abc import Mapping

pytestmark = pytest.mark.wp("facade")

FONTS = Path(__file__).parent / "fixtures" / "fonts"
HOUSE = fr.settings()
_TABLES: dict[str, Mapping[str, object]] = {
    "lines": HOUSE.table("lines"),
    "dash": HOUSE.table("dash"),
    "heights": cast("Mapping[str, object]", HOUSE.table("font")["heights"]),
}
OTHER = build_library(
    {"module_mm": 1.7},
    {"name": "other", "files": (FONTS / "DejaVuSans.ttf", FONTS / "DejaVuSans-Bold.ttf")},
    _TABLES,
    "the test",
)
KEYS = [symbol.reference.number for symbol in LIBRARY]


def test_the_consumer_setting_changes_the_font_and_the_module() -> None:
    assert OTHER.grid.module_mm == 1.7 != LIBRARY.grid.module_mm
    assert OTHER.font != LIBRARY.font
    assert KEYS, "LIBRARY holds no symbol, so the per-key checks would run on nothing"


@pytest.mark.parametrize("key", KEYS)
def test_a_symbol_is_the_same_under_the_consumer_setting(key: str) -> None:
    assert OTHER.get(key) == LIBRARY.get(key)


def test_the_fixed_grid_fields_are_the_same() -> None:
    assert OTHER.grid.divisions_per_module == LIBRARY.grid.divisions_per_module == G_PER_MODULE
    assert int(PORT_PITCH * OTHER.grid.divisions_per_module) == PORT_PITCH_G
    assert WIRING_GRID == 8


@pytest.mark.parametrize("key", KEYS)
def test_a_body_and_keepout_box_do_not_read_the_font(key: str) -> None:
    symbol = OTHER.get(key)
    assert body_box(symbol, OTHER.font) == body_box(symbol)
    assert keepout_box(symbol, OTHER.font) == keepout_box(symbol)
