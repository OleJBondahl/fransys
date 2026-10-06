"""The two root fixtures build a laid-out model (spec section 10, WP order Part C1)."""


def test_demo_cabinet_builds_a_laid_out_model(demo_cabinet):
    assert demo_cabinet.digests["core"]
    assert demo_cabinet.digests["facet"]
    assert demo_cabinet.digests["layout"]


def test_demo_harness_with_board_builds_a_laid_out_model(demo_harness_with_board):
    assert demo_harness_with_board.digests["core"]
    assert demo_harness_with_board.digests["facet"]
    assert demo_harness_with_board.digests["layout"]
