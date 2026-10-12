"""Every public name and keyword appears in the guide as a backticked whole word (API-DOCS P7).

The public surface is `fr.__all__`, `fr.derive.__all__`, `fransys.colours`, and every keyword
of every public call and `d.*` method, with the `d.layout.profile` and `d.layout.sheet` numbers.
It is collected by introspection; the guide is read, not copied. The test checks presence only:
a review judges the quality of an entry.
"""

import annotationlib
import dataclasses
import enum
import inspect
import re
from importlib.resources import files
lazy from collections.abc import Callable

import fransys as fr
import fransys.colours

from fransys_model.layout import Profile, SheetFormat

_NOT_NUMBERS = {"id", "key", "name", "unit", "ext"}
_SKIPPED = {"self", "cls"}


def _guide_text() -> str:
    pages = files("fransys").joinpath("guide").iterdir()
    return "\n".join(p.read_text(encoding="utf-8") for p in pages if p.name.endswith(".md"))


def _keywords(call: Callable[..., object]) -> set[str]:
    """The named parameters of `call`; `*args` and `**numbers` are not names."""
    try:
        signature = inspect.signature(call, annotation_format=annotationlib.Format.FORWARDREF)
    except TypeError, ValueError:
        return set()
    named = (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
    return {p.name for p in signature.parameters.values() if p.kind in named} - _SKIPPED


def _calls_of(obj: object) -> list[Callable[..., object]]:
    if inspect.isclass(obj):
        if issubclass(obj, (BaseException, enum.Enum)):
            return []
        methods = [f for m, f in inspect.getmembers(obj, callable) if not m.startswith("_")]
        return [obj, *methods]
    return [obj] if inspect.isroutine(obj) else []


def _number_names() -> set[str]:
    """The `d.layout.profile` and `d.layout.sheet` numbers: the model records' own fields."""
    profile = {f.name for f in dataclasses.fields(Profile)} - _NOT_NUMBERS - {"sheet_format"}
    sheet = {f.name for f in dataclasses.fields(SheetFormat)} - _NOT_NUMBERS
    return profile | sheet | {"sheet"}


def public_names() -> set[str]:
    names = set(fr.__all__) | set(fr.derive.__all__) | set(fransys.colours.__all__)
    for name in fr.__all__:
        for call in _calls_of(getattr(fr, name)):
            names |= _keywords(call)
    return names | _number_names()


def mentioned(name: str, guide: str) -> bool:
    return re.search(rf"`[^`\n]*\b{re.escape(name)}\b[^`\n]*`", guide) is not None


def test_the_guide_names_every_public_name_and_keyword():
    guide = _guide_text()
    missing = sorted(n for n in public_names() if not mentioned(n, guide))
    assert not missing, f"{len(missing)} public names lack a backticked guide entry: {missing}"


def test_the_collector_sees_keywords_and_numbers():
    names = public_names()
    assert {"module_mm", "column_gap", "text_height", "build"} <= names
    assert mentioned("a_name", "see `a_name` here")
    assert not mentioned("a_name", "see a_name")
