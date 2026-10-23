"""A consumer's `[reference]` and `[frame]` keys reach the printed position and frame (SO2)."""

lazy from pathlib import Path

import pytest

from fransys_model.derive.footprints import footprints
from fransys_model.derive.frame_labels import frame_labels
from fransys_model.derive.frame_position import position_text
from fransys_model.derive.house_settings import frame_form_of, reference_text_of
from fransys_model.derive.page_reference_text import page_reference_text
from fransys_model.derive.rows_footprints import Extent
from fransys_model.derive.sheet_forms import set_page_text
from fransys_model.layout import Page, Side, layout_of
from fransys_model.vocab.enums import FunctionKind
from fransys_model.vocab.tables import functions

from ._settings_text_builds import consumer_file, skid_model

pytestmark = pytest.mark.wp("facade")


def test_a_reference_sign_is_the_consumers(tmp_path: Path) -> None:
    ours = reference_text_of(skid_model())
    form = reference_text_of(
        skid_model(
            consumer_file(
                tmp_path,
                '[reference]\npage_prefix = "s"\ncell_sep = "-"\n'
                'location_sign = "@"\nset_sep = "_"\n',
            )
        )
    )
    cell = ("1", "A")
    assert position_text(ours, 3, cell, (), 2) == "p2.3:1A"
    assert position_text(form, 3, cell, (), 2) == "s2_3-1A"
    assert position_text(form, 3, cell, ("C1",)) == "@C1s3-1A"
    assert set_page_text(form, 2, 3) == "2_3"


def test_a_page_reference_starts_with_the_consumers_prefix(tmp_path: Path) -> None:
    model = skid_model(consumer_file(tmp_path, '[reference]\npage_prefix = "s"\n'))
    page = next(iter(layout_of(model, Page).values()))
    assert page_reference_text(skid_model(), page).startswith("p")
    assert page_reference_text(model, page).startswith("s")


def test_the_frame_labels_follow_the_consumers_naming_and_order(tmp_path: Path) -> None:
    ours = frame_labels(frame_form_of(skid_model()), 3, 3)
    form = frame_form_of(
        skid_model(
            consumer_file(
                tmp_path,
                '[frame]\nrow_labels = "numbers"\ncolumn_labels = "letters"\n'
                'row_order = "bottom_up"\n',
            )
        )
    )
    assert (ours.columns, ours.rows) == (("1", "2", "3"), ("A", "B", "C"))
    got = frame_labels(form, 3, 3)
    assert (got.columns, got.rows) == (("A", "B", "C"), ("3", "2", "1"))


def test_a_width_sample_sizes_the_coil_table_cells(tmp_path: Path) -> None:
    model = skid_model(consumer_file(tmp_path, '[reference]\nwidth_sample = "/1"\n'))
    coil = next(i for i, f in functions(model).items() if f.kind is FunctionKind.COIL)
    body = Extent(x=0, y=0, width=8, height=8)

    def cells(m):
        foot = footprints(
            m, coil, body=body, slots={}, tag_side=Side.W, text_height=3, step=8, pad=2
        )
        return foot.no_cells + foot.nc_cells

    assert all(c.endswith(" /99.99") for c in cells(skid_model()))
    assert all(c.endswith(" /1") for c in cells(model))
