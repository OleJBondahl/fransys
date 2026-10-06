"""Document drafts: preset, subject, cover and notes text (spec F7)."""

from typing import Any
lazy from pathlib import Path

from fransys_author import Item, Location, Scope
from fransys_author.surface import Device

from fransys_model.kernel import Draft, Id, make_id
from fransys_model.vocab import Document as ModelDocument
from fransys_model.vocab import DocumentPreset, PageKind

from ._origin import caller_origin
from ._subjects import unit_of


def engine_subject(subject: object) -> object:
    """A surface `Device` as its engine `Item`; else as is."""
    if isinstance(subject, Device):
        return subject._item  # noqa: SLF001 -- the facade is the surface's one consumer of the engine handle
    return subject


def _subject_ids(  # noqa: PLR0911 -- one branch per subject kind (spec F7, units spec U3)
    subject: object,
) -> tuple[Id[Any] | None, Id[Any] | None, Id[Any] | None, str | None]:
    """`(location, item, unit, unit_name)`, at most one set, from a subject value.

    `Document.__post_init__` checks exactly one of the four (system: none); not re-checked here.
    `None` is the system's. A `str` stays authored text; `derive.document_unit` resolves it (UN2).
    """
    subject = engine_subject(subject)
    if subject is None:
        return None, None, None, None
    if isinstance(subject, str):
        return None, None, None, subject
    if isinstance(subject, Id):
        if subject.kind == "aspect_node":
            return subject, None, None, None
        if subject.kind == "item":
            return None, subject, None, None
        if subject.kind == "unit":
            return None, None, subject, None
        msg = (
            "a document subject id must be an aspect_node, an item or a unit id, "
            f"not {subject.kind!r}"
        )
        raise TypeError(msg)
    if isinstance(subject, Location):
        return subject.id, None, None, None
    if isinstance(subject, Item):
        return None, subject.id, None, None
    if isinstance(subject, Scope):
        unit = unit_of(
            subject, "a unit Scope document subject", "a Location, Item or unit Id instead"
        )
        return None, None, unit, None
    msg = (
        "a document subject must be a Location, an Item, "
        "a unit Scope with a unit, a model Id, a unit release's name (a str), "
        f"or None (the system preset), not {type(subject).__name__}"
    )
    raise TypeError(msg)


def document(  # noqa: PLR0913 -- the new `logo` argument, page-frame R11
    preset: DocumentPreset,
    subject: object,
    *,
    cover: Path,
    add: tuple[PageKind, ...] = (),
    remove: tuple[PageKind, ...] = (),
    logo: Path | None = None,
) -> Draft:
    """Author a document record from a preset, a subject, and a cover file; returns a `Draft`.

    Reads `cover` (a missing file raises `FileNotFoundError`) and the optional `<stem>.notes.md`
    beside it (absent: no notes page); `logo` is an optional SVG for the title block (missing
    raises). Texts are stored in the record. `subject` is what `d.location(...)` returns, a
    `Device`, a unit release name (`str`) or `None` (the `system` preset only);
    any other value raises `TypeError`. Key: `("document", <cover stem>)`: one stem is one record.

    Does not build, render or read files at render time; has no `notes` argument.
    """
    cover_text = cover.read_text(encoding="utf-8")
    notes_path = cover.with_name(f"{cover.stem}.notes.md")
    notes_text = notes_path.read_text(encoding="utf-8") if notes_path.exists() else None
    logo_text = logo.read_text(encoding="utf-8") if logo is not None else None
    location_id, item_id, unit_id, unit_name = _subject_ids(subject)
    key = ("document", cover.stem)
    record = ModelDocument(
        id=make_id(ModelDocument, key),
        key=key,
        preset=preset,
        location=location_id,
        item=item_id,
        unit=unit_id,
        unit_name=unit_name,
        add=tuple(add),
        remove=tuple(remove),
        cover=cover_text,
        notes=notes_text,
        logo=logo_text,
    )
    draft = Draft()
    draft.add(record, origin=caller_origin())
    return draft
