"""`widest_target_line`: the longest line a reference marker can print (R350)."""

from derive_helpers import frozen_with_library

from fransys_model.derive import printing_document, widest_position_text, widest_target_line
from fransys_model.derive.document_subject import scope_path
from fransys_model.kernel import Draft
from fransys_model.vocab.tables import documents

MODEL = frozen_with_library(Draft())


def test_one_digit_numbers_in_an_8_by_6_frame() -> None:
    assert widest_target_line(MODEL, 1, 8, 6, "9") == "#9-p9:9F +9"


def test_each_extra_digit_of_the_page_or_the_frame_widens_the_line() -> None:
    assert widest_target_line(MODEL, 10, 12, 8, "9") == "#99-p99:99H +9"


def test_the_line_is_the_plus_form_so_no_printed_line_is_longer() -> None:
    from fransys_model.derive.marker_targets import target_lines

    two = target_lines(9, ["p9:9F", "p9:8F"])
    assert all(len(line) <= len(widest_target_line(MODEL, 1, 8, 6, "9")) for line in two)


def test_the_widest_position_text_counts_the_digits_of_the_page() -> None:
    """With fewer than two documents there is no far-document prefix: the far text is the page and the cell too."""
    assert widest_position_text(MODEL, 1, (8, 6), "9", far=()) == "p9:9F"
    assert widest_position_text(MODEL, 2, (12, 8), "9", far=()) == "p99:99H"


def test_a_far_document_leads_the_widest_position_text_with_its_own_scope_path(demo_cabinet) -> None:
    """The prefix is that document's `scope_path`, not the widest of all (R1887); `printing_document` names a document of the model or none."""
    model = demo_cabinet
    doc = next(iter(documents(model)))
    assert widest_position_text(model, 1, (8, 6), "9", far=[doc]) == f"{scope_path(model, doc)} p9:9F"
    assert printing_document(model, None, None) in {None, *documents(model)}
    assert printing_document(MODEL, None, None) is None
