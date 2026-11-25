"""Row packing: plain sizes, no overview types."""

from fransys_layout.engines.overview.pack import pack_rows


def test_pack_rows_follows_the_shape_it_is_given() -> None:
    """O1: breaks if the shape is ignored: a wide shape gives fewer rows than a tall one."""
    sizes = [(100, 100)] * 8
    wide = pack_rows(sizes, shape=(4, 1), gap=10)
    tall = pack_rows(sizes, shape=(1, 4), gap=10)
    assert len({y for _, y in wide}) < len({y for _, y in tall})
    assert pack_rows([], shape=(1, 1), gap=10) == ()
