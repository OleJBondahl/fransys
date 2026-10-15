"""`d.detail.star` refusals: each wrong use raises an `AuthorError` that names the fix."""

import fransys_parts
import pytest
from fransys_author import AuthorError
from fransys_author.surface import design

_TERMINAL = "DEMO-TB-2.5"


def _strips():
    d = design(fransys_parts.load("demo_parts"))
    return d, d.terminal_strip("X2", _TERMINAL), d.terminal_strip("X7", _TERMINAL)


@pytest.mark.parametrize(
    ("make", "fix"),
    [
        (lambda x2, x7: (x2[1], x7[1]), r"one target is d\.detail\.wire\(src, target\)"),
        (lambda x2, _x7: (x2[1], ()), "at least one target"),
        (lambda x2, x7: (x2[1], (x7[1], x2[1])), "src is also one of the targets"),
        (lambda x2, x7: (x2[1].inner, (x7[1], x2[1])), "src is also one of the targets"),
        (lambda x2, x7: (x2[1], (x7[1], x7[1])), "given twice"),
        (lambda x2, x7: (x2[1], (x7[1], x7[1].inner)), "given twice"),
    ],
    ids=["bare_pin", "empty", "src_in_targets", "src_port_in_targets", "twice", "twice_port"],
)
def test_star_refuses_a_wrong_use_and_names_the_fix(make, fix) -> None:
    """Each wrong use raises, and writes no wire before it does."""
    d, x2, x7 = _strips()
    src, targets = make(x2, x7)
    with pytest.raises(AuthorError, match=fix):
        d.detail.star(src, targets)
