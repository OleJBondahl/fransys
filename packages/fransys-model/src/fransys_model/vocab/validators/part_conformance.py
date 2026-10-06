"""Validator: an item's functions and ports match its part's templates (design/vocabulary.md 7)."""

from dataclasses import dataclass
from operator import attrgetter
from typing import TYPE_CHECKING, Any, Final

from fransys_model.kernel import Finding, Severity, key_text
from fransys_model.vocab.tables import (
    function_templates,
    functions,
    items,
    port_templates,
    ports,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Function, Item, Port
    from fransys_model.vocab.templates import FunctionTemplate, PortTemplate

ITEM_PART_MISMATCH: Final[str] = "ITEM_PART_MISMATCH"
ITEM_WITHOUT_PART: Final[str] = "ITEM_WITHOUT_PART"


@dataclass(frozen=True, slots=True)
class _Pairing[I: Function | Port, T: FunctionTemplate | PortTemplate]:
    """Instances set against the templates they should come from."""

    matched: tuple[tuple[T, I], ...]
    missing: tuple[T, ...]
    repeated: tuple[tuple[T, I], ...]
    extra: tuple[I, ...]


@dataclass(frozen=True, slots=True)
class _Index:
    """The four groupings the check reads, built once per model."""

    templates_of: frozendict[Id[Any], tuple[FunctionTemplate, ...]]
    functions_of: frozendict[Id[Any], tuple[Function, ...]]
    pins_of: frozendict[Id[Any], tuple[PortTemplate, ...]]
    ports_of: frozendict[Id[Any], tuple[Port, ...]]


def _group[K, R](records: Iterable[R], key_of: Callable[[R], K]) -> frozendict[K, tuple[R, ...]]:
    grouped: dict[K, list[R]] = {}
    for record in records:
        grouped.setdefault(key_of(record), []).append(record)
    return frozendict({key: tuple(found) for key, found in grouped.items()})


def _pair_up[I: Function | Port, T: FunctionTemplate | PortTemplate](
    instances: tuple[I, ...], templates: tuple[T, ...]
) -> _Pairing[I, T]:
    """Match each template to its instance: the one with the lowest id; later ones are repeats."""
    by_template = _group(sorted(instances, key=attrgetter("id")), lambda i: i.template)
    known = {template.id for template in templates}
    matched: list[tuple[T, I]] = []
    missing: list[T] = []
    repeated: list[tuple[T, I]] = []
    for template in templates:
        found = by_template.get(template.id, ())
        if not found:
            missing.append(template)
            continue
        matched.append((template, found[0]))
        repeated.extend((template, again) for again in found[1:])
    extra = tuple(instance for instance in instances if instance.template not in known)
    return _Pairing(tuple(matched), tuple(missing), tuple(repeated), extra)


def _mismatch(message: str, *subjects: Id[Any]) -> Finding:
    return Finding(
        code=ITEM_PART_MISMATCH, severity=Severity.ERROR, subjects=subjects, message=message
    )


def _differing(*facts: tuple[str, object, object]) -> str:
    """Name the facts, written as (label, instance's, template's), that differ; `""` if none."""
    return " and ".join(label for label, own, declared in facts if own != declared)


def _port_findings(
    item: Item, function: Function, template: FunctionTemplate, index: _Index
) -> list[Finding]:
    where = f"function {function.name!r} of item {key_text(item)}"
    pairing = _pair_up(index.ports_of.get(function.id, ()), index.pins_of.get(template.id, ()))
    found = [
        _mismatch(f"{where} has no port for template {pin.name!r}", item.id, function.id, pin.id)
        for pin in pairing.missing
    ]
    found += [
        _mismatch(f"{where} has a second port for template {pin.name!r}", item.id, port.id)
        for pin, port in pairing.repeated
    ]
    found += [
        _mismatch(
            f"{where} has port {port.name!r}, which no port template declares", item.id, port.id
        )
        for port in pairing.extra
    ]
    for pin, port in pairing.matched:
        differing = _differing(
            ("name", port.name, pin.name),
            ("role", port.role, pin.role),
            ("marking", port.marking, pin.marking),
        )
        if differing:
            message = (
                f"port {port.name!r} of {where} differs from template {pin.name!r} in {differing}"
            )
            found.append(_mismatch(message, item.id, port.id))
    return found


def _item_findings(
    item: Item, templates: tuple[FunctionTemplate, ...], index: _Index
) -> list[Finding]:
    where = f"item {key_text(item)}"
    pairing = _pair_up(index.functions_of.get(item.id, ()), templates)
    found = [
        _mismatch(f"{where} has no function for template {template.name!r}", item.id, template.id)
        for template in pairing.missing
    ]
    found += [
        _mismatch(
            f"{where} has a second function for template {template.name!r}", item.id, function.id
        )
        for template, function in pairing.repeated
    ]
    found += [
        _mismatch(
            f"{where} has function {function.name!r}, which no function template declares",
            item.id,
            function.id,
        )
        for function in pairing.extra
    ]
    for template, function in pairing.matched:
        differing = _differing(
            ("name", function.name, template.name), ("kind", function.kind, template.kind)
        )
        if differing:
            message = (
                f"function {function.name!r} of {where} differs from template "
                f"{template.name!r} in {differing}"
            )
            found.append(_mismatch(message, item.id, function.id))
        found += _port_findings(item, function, template, index)
    return found


def check_part_conformance(model: Model) -> tuple[Finding, ...]:
    """Check every `Item` with a `part` has exactly its part's functions and ports.

    `ITEM_PART_MISMATCH` (`ERROR`), one per discrepancy; `ITEM_WITHOUT_PART` (`INFO`): `part=None`.
    Findings come back sorted by `(code, subjects, message)`.
    """
    index = _Index(
        templates_of=_group(function_templates(model).values(), lambda template: template.part),
        functions_of=_group(functions(model).values(), lambda function: function.item),
        pins_of=_group(port_templates(model).values(), lambda pin: pin.function),
        ports_of=_group(ports(model).values(), lambda port: port.function),
    )
    found: list[Finding] = []
    for item in items(model).values():
        if item.part is None:
            found.append(
                Finding(
                    code=ITEM_WITHOUT_PART,
                    severity=Severity.INFO,
                    subjects=(item.id,),
                    message=f"item {key_text(item)} has no part: its functions are not checked",
                )
            )
        else:
            found += _item_findings(item, index.templates_of.get(item.part, ()), index)
    return tuple(
        sorted(found, key=lambda finding: (finding.code, finding.subjects, finding.message))
    )
