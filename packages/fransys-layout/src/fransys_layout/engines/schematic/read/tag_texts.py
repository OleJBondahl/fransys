"""Reads of the model's tag texts for the tag rules (D6, layout-0085).

The rules of `stages/tags.py` ask for a text per function, and some of those texts raise the
model's `SchemaError` before numbering, so nothing is computed here up front: `tag_texts` binds
each `derive` function to the model and the rule calls it when it needs the text.
"""

from functools import partial
from typing import TYPE_CHECKING

from fransys_layout.stages.tags import TagTexts
from fransys_model.derive.designation import connector_designation
from fransys_model.derive.drawing_text import (
    is_device_terminal,
    item_tag_text,
    point_text,
    strip_tag_text,
    unit_tag_text,
)

if TYPE_CHECKING:
    from fransys_model.kernel import Model


def tag_texts(model: Model) -> TagTexts:
    """The tag texts of `model`, each computed when the rule that needs it calls it."""
    return TagTexts(
        connector_designation=partial(connector_designation, model),
        item_tag_text=partial(item_tag_text, model),
        is_device_terminal=partial(is_device_terminal, model),
        strip_tag_text=partial(strip_tag_text, model),
        point_text=partial(point_text, model),
        unit_tag_text=partial(unit_tag_text, model),
    )
