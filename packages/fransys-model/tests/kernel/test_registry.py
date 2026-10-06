"""Kernel registry: `SchemaError` locators for `register_kind`, `lookup_kind` and
`register_namespaces` (mutmut trial 9ab42bae, work order B1 and its T-locator table).

Kinds and class names are unique per test/parametrize case, following `test_schema.py`'s
convention. `_namespaces_after_core` is process-global and not reset between tests (unlike
`_kinds`, which `tests/conftest.py` restores after every test), so a test that needs a
*different* order already registered seeds one first, only if nothing has registered yet.
"""

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

from fransys_model.kernel import (
    SchemaError,
    lookup_kind,
    register_kind,
    register_namespaces,
    registry,
)


def _cls(name: str) -> type:
    """A throwaway class with a distinct `__name__`, standing in for a record class."""
    return type(name, (), {})


# --- B1: register_namespaces() kind of the "already registered" refusal is order[0] -----------


def test_register_namespaces_refusal_kind_is_core_for_an_empty_order() -> None:
    """An empty order, after a different one is registered, raises with kind "core"."""
    if registry.registered_namespaces() == ("core",):
        register_namespaces("test_registry_b1_seed_empty")
    with pytest.raises(SchemaError) as exc_info:
        register_namespaces()
    assert exc_info.value.kind == "core"


def test_register_namespaces_refusal_kind_is_order_zero_for_a_one_element_order() -> None:
    """A one-element order, after a different one is registered, raises with kind == order[0]."""
    if registry.registered_namespaces() == ("core",):
        register_namespaces("test_registry_b1_seed_one")
    with pytest.raises(SchemaError) as exc_info:
        register_namespaces("some_ns")
    assert exc_info.value.kind == "some_ns"


def test_register_namespaces_refusal_kind_is_core_when_core_is_in_order() -> None:
    """`core` in `order` is always invalid; the refusal's kind is pinned to "core"."""
    with pytest.raises(SchemaError) as exc_info:
        register_namespaces("core", "registry_probe_namespace")
    assert exc_info.value.kind == "core"


# --- T-locator table: register_kind / lookup_kind raise sites pin .kind, not the message -------


def _case_malformed_kind_name() -> tuple[Callable[[], object], str]:
    bad_kind = "Registry_Bad_Kind"
    return (lambda: register_kind(bad_kind, _cls("RegistryMalformedProbe")), bad_kind)


def _case_kind_registered_to_different_class() -> tuple[Callable[[], object], str]:
    kind = "registry_probe_dup_kind"
    register_kind(kind, _cls("RegistryDupProbeA"))
    return (lambda: register_kind(kind, _cls("RegistryDupProbeB")), kind)


def _case_class_registered_under_another_kind() -> tuple[Callable[[], object], str]:
    cls = _cls("RegistrySharedProbeClass")
    register_kind("registry_probe_first_kind", cls)
    second_kind = "registry_probe_second_kind"
    return (lambda: register_kind(second_kind, cls), second_kind)


def _case_lookup_unregistered_kind() -> tuple[Callable[[], object], str]:
    kind = "registry_probe_never_registered"
    return (lambda: lookup_kind(kind), kind)


_RAISE_SITES: dict[str, Callable[[], tuple[Callable[[], object], str]]] = {
    "register_kind-malformed-name": _case_malformed_kind_name,
    "register_kind-different-class": _case_kind_registered_to_different_class,
    "register_kind-class-under-another-kind": _case_class_registered_under_another_kind,
    "lookup_kind-unregistered": _case_lookup_unregistered_kind,
}


@pytest.mark.parametrize("case", list(_RAISE_SITES), ids=list(_RAISE_SITES))
def test_registry_raise_sites_pin_the_schema_error_kind(case: str) -> None:
    """Every `register_kind`/`lookup_kind` `SchemaError` carries its locator kind."""
    act, expected_kind = _RAISE_SITES[case]()
    with pytest.raises(SchemaError) as exc_info:
        act()
    assert exc_info.value.kind == expected_kind
