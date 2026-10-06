"""EA13: every public name of the surface says what it does not do, on a line of its own."""

import inspect
lazy from collections.abc import Iterator

from fransys_author import surface

_DUNDERS = ("__getitem__", "__call__")


def _mro_vars(cls: type) -> dict[str, object]:
    merged: dict[str, object] = {}
    for base in reversed(cls.__mro__[:-1]):
        merged.update(vars(base))
    return merged


def _members(name: str, cls: type) -> Iterator[tuple[str, object]]:
    for member, value in _mro_vars(cls).items():
        func = value.fget if isinstance(value, property) else value
        if (member in _DUNDERS or not member.startswith("_")) and callable(func):
            yield f"{name}.{member}", func


def _public_callables() -> Iterator[tuple[str, object]]:
    for name in surface.__all__:
        obj = getattr(surface, name)
        if not getattr(obj, "__module__", "").startswith("fransys_author.surface"):
            continue
        if callable(obj):
            yield name, obj
        if inspect.isclass(obj):
            yield from _members(name, obj)


def has_does_not(doc: str | None) -> bool:
    """True when one line of `doc` starts with "Does not"."""
    return any(line.strip().startswith("Does not") for line in (doc or "").splitlines())


def test_every_public_callable_has_a_does_not_line() -> None:
    missing = [name for name, obj in _public_callables() if not has_does_not(obj.__doc__)]
    assert not missing, f"no 'Does not' line: {missing}"


def test_the_walk_finds_the_surface_and_the_check_can_fail() -> None:
    found = {name for name, _ in _public_callables()}
    wanted = {"design", "Design.location", "Design.function", "Design.draft"}
    assert wanted | {"Design.device", "Design.wire", "Design.terminal_strip"} <= found
    assert not has_does_not("Declares a place.\n\nIt places nothing.")
    assert not has_does_not(None)
    assert has_does_not("Declares a place.\nDoes not place anything.")
