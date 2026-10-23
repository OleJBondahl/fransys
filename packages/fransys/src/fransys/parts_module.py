"""The typed parts module: one class per part, generated from the loaded libraries."""

import re

from fransys_author import AuthorError
from fransys_parts import load as parts_load

from fransys_model.derive import changeover_functions, part_function_pins, part_records
from fransys_model.kernel import Model, freeze, merge, natural_key
from fransys_model.vocab import (
    Part,
    identifier,
)

_TRIPLE = '"' * 3


def _frozen(sources: tuple[str, ...]) -> Model:
    return freeze(merge(*(parts_load(source) for source in sources)))


def library_digest(*sources: str) -> str:
    """The model digest of the libraries `sources` name: whitespace and load order don't move it."""
    return _frozen(sources).digest


def _ident(text: str) -> str:
    """A part class name from a part number, where `-` separates: `LC1D09-BD` is `LC1D09_BD`."""
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
        "        @override",
        f"        def __getitem__(self, m: {_literal(names)}) -> Pin: ...",
    ]


def _function_class(cls: str, fn: str, pins: list[str], *, changeover: bool) -> list[str]:
    lines = [f"class {cls}__{identifier(fn)}(TypedFn):"]
    if changeover:  # a pin named no/nc wins at run time (_handles), so the stub declares the pin
        taken = {identifier(pin) for pin in pins}
        lines += [f"    {throw}: Throw" for throw in ("no", "nc") if throw not in taken]
    lines += [f"    {identifier(pin)}: Pin" for pin in pins]
    # a bar cut to length writes no pin (PE-BAR amendment 1): its class body is `pass`
    if pins:
        lines += _getitem(pins)
    return [*lines, *(["    pass"] if len(lines) == 1 else []), ""]


def _part_class(cls: str, part: Part, functions: list[tuple[str, list[str]]]) -> list[str]:
    all_pins = [pin for _, pins in functions for pin in pins]
    all_idents = [identifier(pin) for pin in all_pins]
    unique = [pin for pin in all_pins if all_idents.count(identifier(pin)) == 1]
    fn_names = {fn for fn, _ in functions}
    names = (
        f"Literal[{', '.join(map(repr, sorted(fn_names, key=natural_key)))}]"
        if fn_names
        else "Never"
    )
    lines = [
        f"class {cls}(TypedDevice[{names}, {cls!r}]):",
        f"    mpn: ClassVar[str] = {part.mpn!r}",
    ]
    idents = [identifier(fn) for fn, _ in functions]
    lines += [f"    {ident}: {cls}__{ident}" for ident in idents]
    lines += [f"    {identifier(pin)}: Pin" for pin in unique if identifier(pin) not in idents]
    return [*lines, *(_getitem(unique) if unique else []), ""]


def _check_unique(mpn: str, kind: str, names: list[str]) -> None:
    """Raise when two raw names of one part or function share a Python identifier."""
    seen: dict[str, str] = {}
    for name in names:
        ident = identifier(name)
        if ident in seen:
            msg = f"part {mpn!r}: {kind} {seen[ident]!r} and {name!r} map to one name {ident}"
            raise AuthorError(msg)
        seen[ident] = name


def _check_identifiers(mpn: str, functions: list[tuple[str, list[str]]]) -> None:
    """Raise when two function names, or two pins of one function, share an identifier."""
    _check_unique(mpn, "functions", [fn for fn, _ in functions])
    for fn, pins in functions:
        _check_unique(mpn, f"pins of {fn!r}:", pins)


def _named_parts(model: Model) -> list[tuple[str, Part]]:
    named = sorted(
        ((_ident(part.mpn), part) for part in part_records(model)),
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
        "from typing import TYPE_CHECKING, ClassVar, Literal, Never, override",
        "",
        "from fransys import Pin, Throw, TypedDevice, TypedFn",
        "",
        f"SOURCES = ({', '.join(map(repr, sources))},)",
        f"LIBRARY_DIGEST = {digest!r}",
        "",
        "",
    ]


def parts_module(*sources: str) -> str:
    """Detail: the text of the typed parts module for the libraries `sources` name.

    For typed part classes in your editor. Try `fr.design(...)` with an MPN string first.

    Does not write a file: `python -m fransys parts-module` does.
    """
    model = _frozen(sources)
    functions, changeovers = part_function_pins(model), changeover_functions(model)
    body: list[str] = []
    for cls, part in _named_parts(model):
        fns = functions.get(part.id, [])
        _check_identifiers(part.mpn, fns)
        for fn, pins in fns:
            body += _function_class(cls, fn, pins, changeover=(part.id, fn) in changeovers)
        body += [*_part_class(cls, part, fns), ""]
    return "\n".join([*_header(sources, model.digest), *body]).rstrip("\n") + "\n"
