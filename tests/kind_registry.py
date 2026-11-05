"""The record-kind registry snapshot shared by the kernel and model conftests."""

from typing import TYPE_CHECKING

from fransys_kernel import registry

if TYPE_CHECKING:
    from collections.abc import Iterator


def restored_kind_registry() -> Iterator[None]:
    """Yield, then give the registry back the kinds it held, restored in place.

    Tests register throwaway kinds and assert on the exact name; a module that bound
    `registry._kinds` by name still sees the live dict.
    """
    kinds = dict(registry._kinds)
    by_name = {name: list(classes) for name, classes in registry._records_by_name.items()}
    values = dict(registry._value_classes)
    yield
    registry._kinds.clear()
    registry._kinds.update(kinds)
    registry._records_by_name.clear()
    registry._records_by_name.update(by_name)
    registry._value_classes.clear()
    registry._value_classes.update(values)
