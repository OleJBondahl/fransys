"""The readers of the house text records; the home is `derive.facts.house_settings` (SO3).

Re-exported here so `derive` modules and the facade keep one path; a check reads it from facts.
"""

from fransys_model.derive.facts.house_settings import (
    colour_codes_of,
    frame_form_of,
    harness_text_of,
    reference_text_of,
    revision_form_of,
    revision_table_form_of,
    stub_text_of,
    title_block_form_of,
    wire_label_text_of,
    word,
)

__all__ = [
    "colour_codes_of",
    "frame_form_of",
    "harness_text_of",
    "reference_text_of",
    "revision_form_of",
    "revision_table_form_of",
    "stub_text_of",
    "title_block_form_of",
    "wire_label_text_of",
    "word",
]
