"""Decision model-0071: `connector_segments` is the one home of the group-segment rule.

Hand-made label sets, no model: a function prints `-<label>` only when two or more of its
item's functions have a label.
"""

import pytest

from fransys_model.derive import connector_label, connector_segments


@pytest.mark.parametrize(
    ("marking", "name", "expected"),
    [
        (None, "x1", "x1"),
        (None, "", None),
        ("", "x1", None),
        ("X1", "x1", "X1"),
    ],
    ids=["absent-is-the-name", "absent-and-no-name", "empty-is-no-label", "set-is-the-label"],
)
def test_connector_label_is_the_marking_else_the_name_and_empty_is_none(
    marking: str | None, name: str, expected: str | None
) -> None:
    """The one home of the label rule; the model's `_connector_label` and the part lint call it."""
    # MUTATION: connector_label `if marking is None` -> `if not marking` (`""` reads as the name)
    assert connector_label(marking, name) == expected


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


def test_segments_accept_any_iterable_and_align_with_the_input() -> None:
    assert connector_segments(label for label in ("X1", "", "X2", "X3")) == (
        "-X1",
        "",
        "-X2",
        "-X3",
    )
