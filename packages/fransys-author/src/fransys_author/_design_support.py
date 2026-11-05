"""The helpers `design.py` shares between its builder methods: record fields, identity, text.

Nothing here writes a record; `Design` and `Scope` call these and own the writes.
"""

import dataclasses
from typing import TYPE_CHECKING, Any

from fransys_model.layout import Profile as ModelProfile
from fransys_model.vocab import Item as ModelItem
from fransys_model.vocab import Unit as ModelUnit

from .errors import AuthorError
from .handles import Fn, Item, Terminal

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

    from fransys_model.kernel import AuthoringKey, Id, Origin, Record


def _required_and_defaults(cls: type[DataclassInstance], *, exclude: set[str]) -> tuple[tuple[str, ...], dict[str, Any]]:
    """The tunable fields of a record `cls`: its required and its defaulted fields."""
    required: list[str] = []
    defaults: dict[str, Any] = {}
    for field_ in dataclasses.fields(cls):
        if field_.name in exclude:
            continue
        if field_.default is not dataclasses.MISSING:
            defaults[field_.name] = field_.default
        else:
            required.append(field_.name)
    return tuple(required), defaults


_PROFILE_REQUIRED, _PROFILE_DEFAULTS = _required_and_defaults(ModelProfile, exclude={"id", "key", "unit", "ext"})


@dataclasses.dataclass(frozen=True, slots=True)
class _Identity:
    name: str
    tag: str | None


def _identity(name: str | None, tag: str | None) -> _Identity:
    """Resolve `name=`/`tag=` into the key segment and the designation."""
    if name is not None:
        return _Identity(name=name, tag=tag)
    if tag is not None:
        return _Identity(name=tag, tag=tag)
    msg = "give name=, tag=, or both -- one is required"
    raise AuthorError(msg)


def _as_function(value: Fn | Item | Terminal) -> Fn:
    if isinstance(value, Fn):
        return value
    if isinstance(value, Item):
        return value.as_function()
    if isinstance(value, Terminal):
        return value.function
    msg = f"expected a function, an item with one function, or a terminal, not {type(value).__name__}"
    raise AuthorError(msg)


def _stamped(records: tuple[Record, ...], *, unit: Id[ModelUnit] | None, external: bool) -> tuple[Record, ...]:
    """Stamp `unit` and `external` onto the `Item` record `instantiate()` made."""
    return tuple(dataclasses.replace(record, unit=unit, external=external) if isinstance(record, ModelItem) else record for record in records)


def _validated_fields(given: dict[str, Any], required: tuple[str, ...], defaults: dict[str, Any], *, what: str) -> dict[str, Any]:
    allowed = set(required) | set(defaults)
    unknown = sorted(set(given) - allowed)
    if unknown:
        msg = f"{what}() does not have {', '.join(unknown)}; valid: {', '.join(sorted(allowed))}"
        raise AuthorError(msg)
    missing = sorted(set(required) - set(given))
    if missing:
        msg = f"{what}() is missing {', '.join(missing)}"
        raise AuthorError(msg)
    return {**defaults, **given}


def _strip_text(strip_key: AuthoringKey | None) -> str:
    return "none" if strip_key is None else "'" + "/".join(strip_key) + "'"


def _name_clash_message(record: Record, first: Origin | None = None, again: Origin | None = None) -> str:
    """A different record under the key, or with `first` and `again` the same Item key added twice."""
    label = "/".join(record.key)
    kind = vars(type(record)).get("__kind__", "record")
    if first is not None and again is not None:
        where = f"first at {first.file}:{first.line}, again at {again.file}:{again.line}"
        return f"'{label}' was already added to this design ({where}); keep the handle from the first call"
    fix = "Call .scale once per channel" if kind == "facet.scaling" else "use a different name= or tag="
    return f"'{label}' already names a different {kind} record in this scope; {fix}"
