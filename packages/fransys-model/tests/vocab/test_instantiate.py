"""Tests: `vocab.instantiate` and `PartBundle`."""

import dataclasses
from typing import TYPE_CHECKING, Any

import pytest
from examples import relay_part_bundle

from fransys_model.kernel import SchemaError, make_id

if TYPE_CHECKING:
    from fransys_model.vocab.instantiate import PartBundle

_KEY = ("examples", "relay-1")


def _only[R](records: tuple, record_type: type[R]) -> list[R]:
    return [r for r in records if isinstance(r, record_type)]


# ---- PartBundle refuses what could not be one part's templates --------------------------


def _relay_with(**changes: Any) -> PartBundle:
    return dataclasses.replace(relay_part_bundle(), **changes)


def _rekeyed(template: Any, *segment: str) -> Any:
    """A copy of `template` under another key, so another id."""
    key = (*template.key, *segment)
    return dataclasses.replace(template, key=key, id=make_id(type(template), key))


_REGISTERED_KIND = {
    "function_templates": "function_template",
    "port_templates": "port_template",
    "internal_links": "internal_link",
}


def test_two_function_templates_with_one_name_are_refused() -> None:
    """Names make the keys, so two of one name would collide in the instance."""
    bundle = relay_part_bundle()
    twin = _rekeyed(bundle.function_templates[0], "twin")
    with pytest.raises(SchemaError, match="name") as excinfo:
        _relay_with(function_templates=(*bundle.function_templates, twin))
    assert excinfo.value.record_id == max(twin.id, bundle.function_templates[0].id)
