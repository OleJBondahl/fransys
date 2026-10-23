"""The one reader of each house text record: derive reads a table here, never anywhere else (SO3).

A model the facade did not build holds no record: each accessor then raises, naming the table.
"""

from fransys_model.kernel import Model, SchemaError
from fransys_model.layout import (
    ColourCodes,
    FrameForm,
    HarnessText,
    ReferenceText,
    RevisionForm,
    RevisionTableForm,
    StubText,
    TitleBlockForm,
    WireLabelText,
    Words,
    layout_of,
)
from fransys_model.vocab.tables import kind_of

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


def _one[R](model: Model, record_type: type[R]) -> R:
    """The one record of `record_type`; raises naming its table when the facade wrote none."""
    found = layout_of(model, record_type)
    if not found:
        kind = kind_of(record_type)
        msg = (
            f"this model carries no {kind} record, so it has no text for that settings table: "
            "build it through `fransys.build`, which writes the records from `fr.settings`"
        )
        raise SchemaError(msg, kind=kind)
    return next(iter(found.values()))


def reference_text_of(model: Model) -> ReferenceText:
    """The `[reference]` record of `model`."""
    return _one(model, ReferenceText)


def frame_form_of(model: Model) -> FrameForm:
    """The `[frame]` record of `model`."""
    return _one(model, FrameForm)


def stub_text_of(model: Model) -> StubText:
    """The `[stub]` record of `model`."""
    return _one(model, StubText)


def wire_label_text_of(model: Model) -> WireLabelText:
    """The `[wire_label]` record of `model`."""
    return _one(model, WireLabelText)


def harness_text_of(model: Model) -> HarnessText:
    """The `[harness]` record of `model`."""
    return _one(model, HarnessText)


def colour_codes_of(model: Model) -> ColourCodes:
    """The `[colours]` record of `model`."""
    return _one(model, ColourCodes)


def title_block_form_of(model: Model) -> TitleBlockForm:
    """The `[title_block]` record of `model`."""
    return _one(model, TitleBlockForm)


def revision_table_form_of(model: Model) -> RevisionTableForm:
    """The `[revision_table]` record of `model`."""
    return _one(model, RevisionTableForm)


def revision_form_of(model: Model) -> RevisionForm:
    """The `[revision]` record of `model`."""
    return _one(model, RevisionForm)


def word(model: Model, key: str) -> str:
    """The printed word `key` of the `[words]` table; raises naming the key when it is absent."""
    table = _one(model, Words).words
    if key not in table:
        msg = f'[words] has no key "{key}"; known: {", ".join(table)}'
        raise SchemaError(msg, kind=kind_of(Words))
    return table[key]
