"""The typed parts module: one class per part, generated from the loaded libraries (EA4)."""

import re
from collections import defaultdict

from fransys_author import AuthorError
from fransys_parts import load as parts_load

from fransys_model.kernel import Model, freeze, merge
from fransys_model.vocab import Part, function_templates, marking_key, parts, port_templates

_TRIPLE = '"' * 3


def _frozen(sources: tuple[str, ...]) -> Model:
    return freeze(merge(*(parts_load(source) for source in sources)))


def library_digest(*sources: str) -> str:
    """The model digest of the libraries `sources` name: whitespace and load order don't move it."""
    return _frozen(sources).digest


def _ident(text: str) -> str:
    name = re.sub(r"\W", "_", text)
    return f"P_{name}" if name[0].isdigit() else name


def _literal(names: list[str]) -> str:
    values = []
    for name in names:
        values.append(repr(name))
        if name.isdigit():
            values.append(name)  # Q1[2] as well as Q1["2"]
    return f"Literal[{', '.join(values)}]"


def _getitem(names: list[str]) -> list[str]:
    return [
        "    if TYPE_CHECKING:",
        f"        def __getitem__(self, m: {_literal(names)}) -> Pin: ...",
    ]


def _function_class(cls: str, fn: str, pins: list[str]) -> list[str]:
    lines = [f"class {cls}__{_ident(fn)}(TypedFn):"]
    lines += [f"    {pin}: Pin" for pin in pins if pin.isidentifier()]
    return [*lines, *_getitem(pins), ""]


def _part_class(cls: str, part: Part, functions: list[tuple[str, list[str]]]) -> list[str]:
    all_pins = [pin for _, pins in functions for pin in pins]
    unique = [pin for pin in all_pins if all_pins.count(pin) == 1]
    fn_names = {fn for fn, _ in functions}
    names = (
        f"Literal[{', '.join(map(repr, sorted(fn_names, key=marking_key)))}]"
        if fn_names
        else "Never"
    )
    lines = [
        f"class {cls}(TypedDevice[{names}, {cls!r}]):",
        f"    mpn: ClassVar[str] = {part.mpn!r}",
    ]
    lines += [f"    {_ident(fn)}: {cls}__{_ident(fn)}" for fn, _ in functions]
    lines += [f"    {pin}: Pin" for pin in unique if pin.isidentifier() and pin not in fn_names]
    return [*lines, *(_getitem(unique) if unique else []), ""]


def _functions_of(model: Model) -> dict[object, list[tuple[str, list[str]]]]:
    """Each part's functions and pin names, sorted: the frozen tables keep no declaration order."""
    pins_of = defaultdict(list)
    for port in port_templates(model).values():
        pins_of[port.function].append(port.name)
    for pins in pins_of.values():
        pins.sort(key=marking_key)
    by_part = defaultdict(list)
    for template in function_templates(model).values():
        by_part[template.part].append((template.name, pins_of[template.id]))
    return {part: sorted(fns, key=lambda fn: marking_key(fn[0])) for part, fns in by_part.items()}


def _named_parts(model: Model) -> list[tuple[str, Part]]:
    named = sorted(
        ((_ident(part.mpn), part) for part in parts(model).values()),
        key=lambda item: (item[1].mpn, item[1].manufacturer),
    )
    seen: dict[str, str] = {}
    for name, part in named:
        if name in seen:
            msg = f"parts {seen[name]!r} and {part.mpn!r} map to one class name {name}"
            raise AuthorError(msg)
        seen[name] = part.mpn
    return named


def _header(sources: tuple[str, ...], digest: str) -> list[str]:
    names = ", ".join(sources)
    return [
        (
            f"{_TRIPLE}Generated from {names}. Do not edit: "
            f"regenerate with python -m fransys parts-module.{_TRIPLE}"
        ),
        "",
        "from typing import TYPE_CHECKING, ClassVar, Literal, Never",
        "",
        "from fransys import Pin, TypedDevice, TypedFn",
        "",
        f"SOURCES = ({', '.join(map(repr, sources))},)",
        f"LIBRARY_DIGEST = {digest!r}",
        "",
        "",
    ]


def parts_module(*sources: str) -> str:
    """The text of the typed parts module for the libraries `sources` name (`fr.parts` names).

    Does not write a file: `python -m fransys parts-module` does.
    """
    model = _frozen(sources)
    functions = _functions_of(model)
    body: list[str] = []
    for cls, part in _named_parts(model):
        fns = functions.get(part.id, [])
        for fn, pins in fns:
            body += _function_class(cls, fn, pins)
        body += [*_part_class(cls, part, fns), ""]
    return "\n".join([*_header(sources, model.digest), *body]).rstrip("\n") + "\n"
