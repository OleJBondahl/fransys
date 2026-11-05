"""The title block's words and the text forms of its fields; render measures them (pdf-0010).

The measuring moved to `fransys_render` (CC1, model-0373); here only the strings are made.
"""

from fransys_model.vocab.tables import documents
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab import Document

from .facts.house_settings import title_block_form_of, word
from .rows_sheet_pages import DocumentSheets, FieldForms, TitleBlockText
from .title_block import document_facts

__all__ = ["title_block_forms", "title_block_words"]

_DOCUMENT_FIELDS = ("title", "number", "customer", "revision", "revision_date", "author")


def title_block_words(model: Model) -> TitleBlockText:
    """The labels of the `[title_block]` record's cells, in its order, and the cut mark."""
    cells = title_block_form_of(model).fields
    return TitleBlockText(
        labels=frozendict({cell: word(model, cell) for cell in cells}),
        ellipsis=word(model, "ellipsis"),
    )


def title_block_forms(model: Model, document: Id[Document], sheets: DocumentSheets) -> tuple[FieldForms, ...]:
    """The text forms of the fields a title block prints.

    The six document-level ones, then each checked page's; `forms`: preferred, then shorter.
    """
    record = documents(model)[document]
    facts = dict(zip(_DOCUMENT_FIELDS, document_facts(model, record.id), strict=True))
    found = [FieldForms(field=f, forms=(facts[f],), where="document") for f in _DOCUMENT_FIELDS]
    seen: set[str] = set()
    for page in (p for p in sheets.pages if p.group):
        fields = page.fields
        if page.group not in seen:
            seen.add(page.group)
            found.append(FieldForms(field="scope", forms=(fields.scope,), where=page.group))
        titles = (fields.page_title, *fields.page_title_shorter)
        found.append(FieldForms(field="page_title", forms=titles, where=page.where))
        found.append(FieldForms(field="sheet_counter", forms=(fields.sheet_counter,), where=page.where))
    return tuple(found)
