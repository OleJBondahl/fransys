"""Document drafts: preset, subject, cover and notes text."""

from typing import Any
lazy from pathlib import Path

from fransys_author import Item, Location, Scope
from fransys_author.surface import Design, Device

from fransys_model.derive import subject_kind, subject_kind_text
from fransys_model.kernel import Draft, Id, make_id
from fransys_model.vocab import Document as ModelDocument
from fransys_model.vocab import DocumentPreset, PageKind, SubjectKind

from ._origin import caller_origin
from ._subjects import unit_of


def engine_subject(subject: object) -> object:
    """A surface `Device` as its engine `Item`; else as is."""
    if isinstance(subject, Device):
        return subject._item  # noqa: SLF001 -- the facade is the surface's one consumer of the engine handle
    return subject


def _id_subject_ids(
    subject: Id[Any],
) -> tuple[Id[Any] | None, Id[Any] | None, Id[Any] | None, str | None]:
    kind = subject_kind(subject)
    if kind is SubjectKind.ASPECT_NODE:
        return subject, None, None, None
    if kind is SubjectKind.ITEM:
        return None, subject, None, None
    if kind is SubjectKind.UNIT:
        return None, None, subject, None
    msg = (
        "a document subject id must be an aspect_node, an item or a unit id, "
        f"not {subject_kind_text(subject)!r}"
    )
    raise TypeError(msg)


def _subject_ids(
    subject: object,
) -> tuple[Id[Any] | None, Id[Any] | None, Id[Any] | None, str | None]:
    """`(location, item, unit, unit_name)`, at most one set, from a subject value.

    `Document.__post_init__` checks exactly one of the four (system: none); not re-checked here.
    `None` is the system's. A `str` stays authored text; `derive.document_unit` resolves it.
    """
    subject = engine_subject(subject)
    if subject is None:
        return None, None, None, None
    if isinstance(subject, str):
        return None, None, None, subject
    if isinstance(subject, Id):
        return _id_subject_ids(subject)
    if isinstance(subject, Location):
        return subject.id, None, None, None
    if isinstance(subject, Item):
        return None, subject.id, None, None
    unit = Design._added_unit(subject)  # noqa: SLF001 -- the facade is the surface's one consumer
    if unit is None and isinstance(subject, Scope):
        unit = unit_of(
            subject, "a unit Scope document subject", "a Location, Item or unit Id instead"
        )
    if unit is not None:
        return None, None, unit, None
    msg = (
        "a document subject must be a Location, an Item, "
        "a unit Scope with a unit, what `d.add` returned, a model Id, "
        "a unit release's name (a str), "
        f"or None (the system preset), not {type(subject).__name__}"
    )
    raise TypeError(msg)


def _document_key(
    stem: str, preset: DocumentPreset, subject: tuple[object, ...]
) -> tuple[str, ...]:
    """The key: cover stem, preset and subject, so documents may share one cover path."""
    named = [str(one.value if isinstance(one, Id) else one) for one in subject if one is not None]
    return ("document", stem, preset.name, *named)


def document(  # noqa: PLR0913 -- the new `logo` argument
    preset: DocumentPreset,
    subject: object,
    *,
    cover: Path,
    add: tuple[PageKind, ...] = (),
    remove: tuple[PageKind, ...] = (),
    logo: Path | None = None,
    notice: str = "",
) -> Draft:
    """Output: author a document record from a preset, a subject and a cover file.

    Returns a `Draft`.

    Reads `cover` (a missing file raises `FileNotFoundError`) and the optional `<stem>.notes.md`
    beside it (absent: no notes page); `logo` is an optional SVG for the title block (missing
    raises); `notice` is the title block's IP notice
    text. Texts are stored in the record. `subject` is what `d.location(...)` returns, a
    `Device`, a unit release name (`str`) or `None` (the `system` preset only);
    any other value raises `TypeError`. Key: the cover stem, preset and subject, so documents
    may share a cover path.

    Does not build, render or read files at render time; has no `notes` argument.
    """
    cover_text = cover.read_text(encoding="utf-8")
    notes_path = cover.with_name(f"{cover.stem}.notes.md")
    notes_text = notes_path.read_text(encoding="utf-8") if notes_path.exists() else None
    logo_text = logo.read_text(encoding="utf-8") if logo is not None else None
    location_id, item_id, unit_id, unit_name = _subject_ids(subject)
    key = _document_key(cover.stem, preset, (location_id, item_id, unit_id, unit_name))
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
        notice=notice,
    )
    draft = Draft()
    draft.add(record, origin=caller_origin())
    return draft
