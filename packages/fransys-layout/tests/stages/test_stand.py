"""`stand.out_dir`: the y sign of "out" from a port, the one fact `tier_offset` multiplies by."""

from fransys_layout.stages.texts.stand import out_dir


def test_out_dir_is_down_for_south_and_up_for_north() -> None:
    assert out_dir(south=True) == 1
    assert out_dir(south=False) == -1
