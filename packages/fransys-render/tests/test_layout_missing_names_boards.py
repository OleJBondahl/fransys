"""`LAYOUT_MISSING` names each board the build reports as having nets that are not drawn."""

from fransys_render.check import _boards_of

from fransys_model.kernel import Finding, Id, Severity


def _finding(code: str, board: Id) -> Finding:
    return Finding(code=code, severity=Severity.WARNING, subjects=(board,), message="m", fix="f")


def test_the_boards_are_the_subjects_of_the_reported_code_only() -> None:
    board, other = Id(kind="item", value="b1"), Id(kind="item", value="b2")
    built = (_finding("BOARD_NETS_NOT_DRAWN", board), _finding("LONE_CELL", other))
    assert _boards_of(built) == (board,)
    assert _boards_of(()) == ()
