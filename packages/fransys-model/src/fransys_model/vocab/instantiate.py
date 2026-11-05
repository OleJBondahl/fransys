"""Vocabulary: the `PartBundle` a part and its templates make (design/vocabulary.md 7); `fransys_author.instantiate` stamps it."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fransys_model.kernel import Id, Record, SchemaError, key_text

from .templates import FunctionTemplate, InternalLink, Part, PortTemplate

if TYPE_CHECKING:
    from collections.abc import Callable


def _refuse(message: str, kind: str, record: Record) -> SchemaError:
    return SchemaError(message, kind=kind, record_id=record.id)


def _by_id[R: Record](records: tuple[R, ...]) -> list[R]:
    """`records` in id order, so which record a refusal names never depends on listing order."""
    return sorted(records, key=lambda record: record.id)


def _refuse_repeated_ids(records: tuple[FunctionTemplate | PortTemplate | InternalLink, ...], kind: str) -> None:
    previous: Id[object] | None = None
    for record in _by_id(records):
        if record.id == previous:
            msg = f"{kind.replace('_', ' ')} {key_text(record)} is listed twice"
            raise _refuse(msg, kind, record)
        previous = record.id


def _refuse_repeated_names[R: FunctionTemplate | PortTemplate](records: tuple[R, ...], kind: str, scope_of: Callable[[R], Id[object]]) -> None:
    """Names make the instance keys, so within one scope two of a name would collide."""
    seen: set[tuple[Id[object], str]] = set()
    for record in sorted(records, key=lambda r: (scope_of(r), r.name, r.id)):
        slot = (scope_of(record), record.name)
        if slot in seen:
            msg = f"two {kind.replace('_', ' ')}s share the name {record.name!r}"
            raise _refuse(msg, kind, record)
        seen.add(slot)


@dataclass(frozen=True, slots=True, kw_only=True)
class PartBundle:
    """A part and its full template set, ready to stamp onto an `Item` (design/vocabulary.md 7).

    A plain frozen dataclass, not a `@value`: it holds table records inline, which the kernel
    refuses in a value (decision 0012). It refuses a set of templates that could not belong
    to one part, so `instantiate` never meets one.

    Example: the invented relay bundle (design/examples.md 11) carries the relay
    `Part`, its `coil`/`no_1`/`co_1` `FunctionTemplate`s, their `PortTemplate`s, and the `co_1`
    `InternalLink`s.
    """

    part: Part
    function_templates: tuple[FunctionTemplate, ...]
    port_templates: tuple[PortTemplate, ...]
    internal_links: tuple[InternalLink, ...]

    def __post_init__(self) -> None:
        """Refuse what could not be one part's templates; a pin name may repeat across functions.

        Raises `SchemaError` if a template belongs to another part, or a port or link end names one
        not in the bundle; if one is listed twice; if names repeat among one scope's templates.
        """
        _refuse_foreign_templates(self)
        _refuse_repeated_ids(self.function_templates, "function_template")
        _refuse_repeated_ids(self.port_templates, "port_template")
        _refuse_repeated_ids(self.internal_links, "internal_link")
        _refuse_repeated_names(self.function_templates, "function_template", lambda t: t.part)
        _refuse_repeated_names(self.port_templates, "port_template", lambda t: t.function)


def _refuse_foreign_templates(bundle: PartBundle) -> None:
    """Refuse a template of another part, or a port or link end outside `bundle`."""
    function_ids = {template.id for template in bundle.function_templates}
    port_ids = {template.id for template in bundle.port_templates}
    for function_template in _by_id(bundle.function_templates):
        if function_template.part != bundle.part.id:
            msg = f"function template {function_template.name!r} belongs to another part"
            raise _refuse(msg, "function_template", function_template)
    for port_template in _by_id(bundle.port_templates):
        if port_template.function not in function_ids:
            msg = f"port template {port_template.name!r} names a function template outside the bundle"
            raise _refuse(msg, "port_template", port_template)
    for link in _by_id(bundle.internal_links):
        if link.a not in port_ids or link.b not in port_ids:
            msg = f"internal link {key_text(link)} joins a port template outside the bundle"
            raise _refuse(msg, "internal_link", link)
