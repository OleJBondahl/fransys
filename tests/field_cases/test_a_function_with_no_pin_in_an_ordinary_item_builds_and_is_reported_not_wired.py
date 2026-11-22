"""Field case: an ordinary item whose one function declares no pin (a part file refuses one; a raw record carries it).
The bug (KI-1070): the box sizer ranked the empty port list and the build raised ValueError (min of an empty sequence).
Fixed (R2534, NO-SILENT-DROP): `_by_rank` reads no ports as all-tie; `without_loose` leaves the symbol out and reports FUNCTION_NOT_WIRED."""

import fransys as fr
from _model_build_cover import system_document

from fransys_model.kernel import Draft, Origin, make_id
from fransys_model.vocab import Project, Revision
from fransys_model.vocab.core import Function, Item
from fransys_model.vocab.enums import FunctionKind, PartCategory
from fransys_model.vocab.templates import FunctionTemplate, Part

_ORIGIN = Origin(file="tests/field_cases/pinless.py", line=1, note="invented")


def _pinless_draft() -> Draft:
    part = Part(
        id=make_id(Part, ("p",)),
        key=("p",),
        mpn="FLD-NOTE",
        manufacturer="Demo",
        description="Invented",
        category=PartCategory.GENERIC,
        class_code="H",
    )
    template = FunctionTemplate(id=make_id(FunctionTemplate, ("p", "fn")), key=("p", "fn"), part=part.id, name="fn", kind=FunctionKind.GENERIC)
    item = Item(id=make_id(Item, ("i",)), key=("i",), part=part.id, parent=None, position=None, tag="H1", description="Invented")
    function = Function(id=make_id(Function, ("i", "fn")), key=("i", "fn"), item=item.id, template=template.id, name="fn", kind=FunctionKind.GENERIC)
    project = Project(id=make_id(Project, ("project",)), key=("project",), title="Demo", number="P-1", customer="Demo Co", revision=1, author="d")
    revision = Revision(
        id=make_id(Revision, ("revision", "1", "1")),
        key=("revision", "1", "1"),
        release=None,
        version=1,
        revision=1,
        date="2026-09-22",
        text="First",
        created="XX",
    )
    draft = Draft()
    draft.extend([project, revision, part, template, item, function], origin=_ORIGIN)
    return draft


def test_a_pinless_function_builds_and_is_reported_not_wired() -> None:
    result = fr.build(_pinless_draft(), system_document())
    assert [(f.code, f.message) for f in result.findings] == [("FUNCTION_NOT_WIRED", "function H1:fn has no wired pin, so it is left off the page")]
