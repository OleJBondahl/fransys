"""The facade writes the build's paper records from `Settings` and refuses authored ones (ST4)."""

from decimal import Decimal
lazy from pathlib import Path

import fransys as fr
import pytest
from fransys._paper import with_paper

from fransys_model.kernel import Draft, Origin, Record, SchemaError, make_id
from fransys_model.layout import PaperChoice, SheetFormat, layout_of, sheet_for, sheet_format_of

pytestmark = pytest.mark.wp("facade")

_ORIGIN = Origin(file="test_paper_record.py", line=1, note="planted")
KIND = fr.PageKind


def _sheet_name(settings: fr.Settings, kind: fr.PageKind) -> str:
    model = fr.build(fr.design("demo_parts"), settings=settings).model
    return sheet_for(model, kind).name


def test_the_house_build_draws_schematics_on_a3_and_the_block_diagram_on_a2() -> None:
    house = fr.settings()
    assert _sheet_name(house, KIND.SCHEMATIC) == "A3 landscape"
    assert _sheet_name(house, KIND.BLOCK_DIAGRAM) == "A2 landscape"


def test_a_default_of_a2_draws_the_pages_with_no_sheet_on_a2(tmp_path: Path) -> None:
    path = tmp_path / "fransys.toml"
    path.write_text('[paper]\ndefault = "A2"\n', encoding="utf-8")
    model = fr.build(fr.design("demo_parts"), settings=fr.settings(path)).model
    assert sheet_format_of(model, None).name == "A2 landscape"
    assert sheet_for(model, KIND.SCHEMATIC).name == "A2 landscape"


def test_a_per_kind_choice_moves_that_kind_only() -> None:
    chosen = fr.settings(paper={KIND.BLOCK_DIAGRAM: "A3"})
    assert _sheet_name(chosen, KIND.BLOCK_DIAGRAM) == "A3 landscape"
    assert _sheet_name(chosen, KIND.SCHEMATIC) == "A3 landscape"
    both = fr.settings(paper={KIND.SCHEMATIC: "A2", KIND.BLOCK_DIAGRAM: "A3"})
    assert _sheet_name(both, KIND.SCHEMATIC) == "A2 landscape"
    assert _sheet_name(both, KIND.COVER) == "A3 landscape"


def test_the_records_are_keyed_by_format_name() -> None:
    model = fr.build(fr.design("demo_parts")).model
    assert {s.key for s in layout_of(model, SheetFormat).values()} == {
        ("build", "paper", "A2"),
        ("build", "paper", "A3"),
    }
    assert len(layout_of(model, PaperChoice)) == 1


def test_a_second_paper_choice_is_refused() -> None:
    once = fr.build(fr.design("demo_parts")).model
    with pytest.raises(SchemaError, match=r"layout\.paper"):
        with_paper(once, fr.settings())


def _planted(record: Record) -> Draft:
    draft = Draft()
    draft.extend([record], origin=_ORIGIN)
    return draft


def test_an_authored_paper_choice_is_refused() -> None:
    key = ("planted", "paper")
    other = make_id(SheetFormat, key)
    record = PaperChoice(id=make_id(PaperChoice, key), key=key, default=other)
    with pytest.raises(SchemaError, match=r"layout\.paper"):
        fr.build(_planted(record))


def test_an_authored_sheet_keyed_by_a_format_name_is_refused() -> None:
    key = ("build", "paper", "A3")
    record = SheetFormat(
        id=make_id(SheetFormat, key),
        key=key,
        name="A3",
        width_mm=1,
        height_mm=1,
        content_x_mm=0,
        content_y_mm=0,
        content_width_mm=1,
        content_height_mm=1,
        frame_columns=1,
        frame_rows=1,
        module_mm=Decimal(1),
    )
    with pytest.raises(SchemaError, match=r"layout\.sheet_format"):
        fr.build(_planted(record))
