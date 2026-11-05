"""The title block frame labels."""

from derive_helpers import house_record

from fransys_model.derive import frame_labels
from fransys_model.layout import FrameForm


def test_frame_labels_number_the_columns_and_letter_the_rows():
    """An 8 by 6 frame reads 1..8 across and A..F down."""
    labels = frame_labels(house_record(FrameForm), 8, 6)
    assert labels.columns == ("1", "2", "3", "4", "5", "6", "7", "8")
    assert labels.rows == ("A", "B", "C", "D", "E", "F")
