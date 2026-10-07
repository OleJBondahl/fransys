"""`heads_group`: which marker heads a reference group (RR-O5, layout-0132)."""

import pytest

from fransys_model.derive.reference_heads import heads_group


@pytest.mark.parametrize(
    ("star", "side", "named", "heads"),
    [
        ("", "owner", False, True),
        ("", "user", False, False),
        ("ref", "user", False, True),
        ("branch", "owner", False, True),
        ("branch", "user", False, False),
        ("off", "owner", False, False),
        ("off", "owner", True, True),
    ],
)
def test_the_head_of_a_group_by_star_side_and_branches(
    star: str, side: str, *, named: bool, heads: bool
) -> None:
    """A reference heads; a cut or split pair by its owner; an off stub only when named."""
    # CAN-FAIL: reference_heads.py `heads_group`: `return named` -> `return False` fails the
    #     last row; `side == OWNER` -> `side == USER` fails the first two
    assert heads_group(star, side, named=named) is heads
