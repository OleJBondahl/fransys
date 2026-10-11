"""Decision model-0071: `connector_segments` is the one home of the group-segment rule.

Hand-made label sets, no model: a function prints `-<label>` only when two or more of its
item's functions have a label.
"""

import pytest

from fransys_model.derive import connector_segments


@pytest.mark.parametrize(
    ("labels", "expected"),
    [
        ((), ()),
        (("J1",), ("",)),
        (("X1", "X2"), ("-X1", "-X2")),
        (("X1", ""), ("", "")),
        (("X1", "", "X2"), ("-X1", "", "-X2")),
        (("", ""), ("", "")),
        ((None, "X1", None), ("", "", "")),
        (("X1", None, "X2"), ("-X1", "", "-X2")),
    ],
)
def test_segments_print_only_with_two_or_more_labels(
    labels: tuple[str | None, ...], expected: tuple[str, ...]
) -> None:
    # MUTATION: connector_segments `<= 1` -> `<= 0` (a lone label prints `-J1`)
    assert connector_segments(labels) == expected
