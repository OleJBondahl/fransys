"""Layout's table height and heading room are `derive.contact_rows`' (model-0216, CR2)."""

from fransys_layout.engines.schematic.read.house import DEFAULT_PROFILE
from fransys_layout.stages.images import table_height
from fransys_model.derive.contact_rows import table_geometry


def test_a_stage_table_is_as_high_as_the_derive_geometry_says() -> None:
    step, pad = DEFAULT_PROFILE.text_height, DEFAULT_PROFILE.marker_padding
    for rows in range(8):
        assert (
            table_height(rows, DEFAULT_PROFILE)
            == table_geometry(rows, step, pad, headed=False).height
        )


def test_the_heading_room_is_the_columns_offset_of_a_headed_table() -> None:
    step, pad = DEFAULT_PROFILE.text_height, DEFAULT_PROFILE.marker_padding
    assert DEFAULT_PROFILE.heading_room == table_geometry(1, step, pad, headed=True).columns
