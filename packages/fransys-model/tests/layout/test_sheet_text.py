"""SI3's sheet text: the number in the first set, `set.number` after it (PAGES-TITLES)."""

from dataclasses import replace

from layout_examples import drawing_set, drawn_function, group_node, page, sheet_format

from fransys_model.derive import sheet_text
from fransys_model.kernel import Draft, Id, Origin, freeze


def test_a_sheet_text_is_the_number_in_the_first_set_and_set_dot_number_after_it() -> None:
    first, second = (
        drawing_set(),
        replace(
            drawing_set(),
            id=Id(kind="layout.drawing_set", value="9" * 32),
            key=("d", "2"),
            number=2,
        ),
    )
    page_one = page()
    page_two = replace(
        page_one,
        id=Id(kind="layout.page", value="8" * 32),
        key=("p", "2"),
        drawing_set=second.id,
        number=3,
    )
    draft = Draft()
    draft.extend(
        (group_node(), *drawn_function(), sheet_format(), first, second, page_one, page_two),
        origin=Origin(file="test_sheet_text.py", line=1, note="fixture"),
    )
    model = freeze(draft)
    assert (sheet_text(model, page_one), sheet_text(model, page_two)) == ("1", "2.3")
