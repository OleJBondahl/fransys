"""A consumer `[grid]` and `[font]` hold for the whole build (SETTINGS ST3, ST4, ST5)."""

from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import fransys as fr
import pytest
from fontTools.ttLib import TTFont
from fransys._settings_library import build_library, library_of
from fransys_pdf._lists import bom_page
from symdef import Weight, text_width

from electrical_symbols import LIBRARY
from fransys_model.derive import document_rows, mm_per_division
from fransys_model.layout import DrawingLibrary, PaperChoice, SheetFormat, layout_of

pytestmark = pytest.mark.wp("facade")

FONTS = Path(__file__).parent / "fixtures" / "fonts"
REGULAR, BOLD = FONTS / "DejaVuSans.ttf", FONTS / "DejaVuSans-Bold.ttf"
FILES = f'files = ["{REGULAR}", "{BOLD}"]\n'


def _file(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "fransys.toml"
    path.write_text(text, encoding="utf-8")
    return path


def _built(settings: fr.Settings):
    d = fr.design("demo_parts", place="CAB")
    d.location("CAB", "Cabinet")
    d.terminal_strip("X1", "DEMO-TB-2.5", 6)
    return fr.build(d, settings=settings).model


def test_a_consumer_module_mm_changes_the_grid_of_the_whole_build(tmp_path: Path) -> None:
    model = _built(fr.settings(_file(tmp_path, "[grid]\nmodule_mm = 2.0\n")))
    (record,) = layout_of(model, DrawingLibrary).values()
    assert record.module_mm == Decimal("2.0")
    (choice,) = layout_of(model, PaperChoice).values()
    sheet = layout_of(model, SheetFormat)[choice.default]
    assert sheet.module_mm == Decimal("2.0")
    assert mm_per_division(model, sheet) == Decimal("2.0") / 8


def test_the_house_build_keeps_the_house_grid() -> None:
    (record,) = layout_of(_built(fr.settings()), DrawingLibrary).values()
    assert record.module_mm == Decimal(str(LIBRARY.grid.module_mm))


def test_a_second_font_measures_widths_equal_to_the_font_tools_advances(tmp_path: Path) -> None:
    settings = fr.settings(_file(tmp_path, f"[font]\nname = 'Vera'\n{FILES}"))
    font = library_of(settings).font
    house = LIBRARY.font
    assert font is not None
    assert house is not None
    face = TTFont(REGULAR)
    cmap, hmtx = cast("dict[int, str]", face.getBestCmap()), cast("Any", face["hmtx"])
    for char in "Hello 123":
        assert font.advances[Weight.NORMAL][char] == hmtx[cmap[ord(char)]][0]
    assert text_width(font, "Hello 123", 1.0) != text_width(house, "Hello 123", 1.0)
    assert dict(font.heights) == dict(house.heights)  # a font swap keeps the text sizes


def test_a_consumer_font_keeps_the_houses_text_heights_and_record(tmp_path: Path) -> None:
    model = _built(fr.settings(_file(tmp_path, f"[font]\n{FILES}")))
    (record,) = layout_of(model, DrawingLibrary).values()
    assert record.font_family == "DejaVu Sans"
    assert record.heights["body"] == Decimal("2.5")


def _widened(tmp_path: Path) -> Path:
    """A copy of the regular fixture whose every advance is eight times wider."""
    font = TTFont(REGULAR)
    hmtx = font["hmtx"]
    for name in hmtx.metrics:
        advance, bearing = hmtx.metrics[name]
        hmtx.metrics[name] = (min(advance * 8, 65535), bearing)
    path = tmp_path / "wide-regular.ttf"
    font.save(path)
    return path


def test_a_font_whose_advances_overflow_a_symbols_text_fails_the_build(tmp_path: Path) -> None:
    wide = _widened(tmp_path)
    text = f'[font]\nfiles = ["{wide}", "{BOLD}"]\n'
    with pytest.raises(fr.SettingsError, match=r"text outside its body after the new settings"):
        fr.settings(_file(tmp_path, text))


def test_the_settings_error_names_the_file(tmp_path: Path) -> None:
    path = _file(tmp_path, "[grid]\nmodule_mm = -1\n")
    with pytest.raises(fr.SettingsError, match=rf"{path.name}.*module_mm"):
        fr.settings(path)


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("[font]\nheights = {huge = 9.0}\n", r'"huge" is not a setting; known: smallest, body'),
        ("[font.heights]\nbody = 'big'\n", r'"body" must be a number'),
        ("[lines]\nbold = 1.0\n", r'"bold" is not a setting; known: normal, thick, rule'),
        ("[dash]\ndashed = [1.0]\n", r"dashed.*symdef|dashed"),
        ("[font]\nfamily = 'X'\n", r'"family" is not a setting; known: name, files'),
        ("[font]\nname = 'x'\n", r"needs `files = \[regular, bold\]`"),
        (
            '[font]\nfiles = ["nope.ttf", "nope-bold.ttf"]\n',
            r"font file .*nope\.ttf does not exist",
        ),
        ('[grid]\nmodule_mm = "wide"\n', r'"module_mm" must be a number'),
        ("[grid]\nwire_pitch = 4\n", r"wire_pitch.*is library data"),
    ],
)
def test_a_wrong_grid_or_font_key_raises_naming_the_key(
    tmp_path: Path, text: str, message: str
) -> None:
    with pytest.raises(fr.SettingsError, match=message):
        fr.settings(_file(tmp_path, text))


def test_only_a_symdef_error_becomes_a_settings_error(monkeypatch):
    import fransys._settings_library as sl

    def broken(**_kwargs):
        msg = "a programming error"
        raise TypeError(msg)

    monkeypatch.setattr(sl, "LIBRARY", SimpleNamespace(lines=(), with_settings=broken))
    with pytest.raises(TypeError, match="a programming error"):
        build_library({"module_mm": 7.0}, {}, {"lines": {}, "dash": {}, "heights": {}}, "test")


def test_a_consumer_height_is_kept_with_the_other_heights(tmp_path: Path) -> None:
    settings = fr.settings(_file(tmp_path, "[font.heights]\nbody = 3.0\n"))
    font = library_of(settings).font
    assert font is not None
    heights = dict(font.heights)
    assert heights["body"] == 3.0
    assert heights["smallest"] == 1.8
    (record,) = layout_of(_built(settings), DrawingLibrary).values()
    assert record.heights["body"] == Decimal("3.0")
    assert record.heights["smallest"] == Decimal("1.8")


def test_a_consumer_line_weight_and_dash_reach_the_library(tmp_path: Path) -> None:
    settings = fr.settings(_file(tmp_path, "[lines]\nrule = 0.3\n[dash]\nlong = [5.0, 2.0]\n"))
    library = library_of(settings)
    assert library.lines[Weight.RULE] == 0.3
    assert library.dash["long"] == (5.0, 2.0)
    (record,) = layout_of(_built(settings), DrawingLibrary).values()
    assert record.lines["rule"] == Decimal("0.3")


def test_a_consumer_table_rule_is_the_stroke_of_the_printed_tables(tmp_path: Path) -> None:
    d = fr.design("demo_parts", place="CAB")
    cabinet = d.location("CAB", "Cabinet")
    d.terminal_strip("X1", "DEMO-TB-2.5", 6)
    (tmp_path / "c.md").write_text("# c\n", encoding="utf-8")
    settings = fr.settings(_file(tmp_path, "[lines]\nrule = 0.3\n"))
    model = fr.build(
        d,
        fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cabinet, cover=tmp_path / "c.md"),
        settings=settings,
    ).model
    (record,) = document_rows(model)
    assert "stroke: 0.3mm" in bom_page(model, record)
    assert "stroke: 0.18mm" not in bom_page(model, record)
