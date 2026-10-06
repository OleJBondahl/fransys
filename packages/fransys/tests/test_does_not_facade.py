"""EA13: every public function of `fransys` says what it does not do, on a line of its own."""

import inspect
lazy from collections.abc import Iterator

import fransys

_NAMES = {
    "build",
    "check",
    "design",
    "diff",
    "document",
    "lint",
    "parts",
    "parts_module",
    "release",
    "verify",
    "write",
}


def _public_functions() -> Iterator[tuple[str, object]]:
    for name in fransys.__all__:
        obj = getattr(fransys, name)
        if inspect.isfunction(obj) and obj.__module__.startswith("fransys."):
            yield name, obj


def has_does_not(doc: str | None) -> bool:
    """True when one line of `doc` starts with "Does not"."""
    return any(line.strip().startswith("Does not") for line in (doc or "").splitlines())


def test_every_public_function_has_a_does_not_line() -> None:
    missing = [name for name, obj in _public_functions() if not has_does_not(obj.__doc__)]
    assert not missing, f"no 'Does not' line: {missing}"


def test_the_walk_finds_the_eleven_functions_and_the_check_can_fail() -> None:
    assert {name for name, _ in _public_functions()} == _NAMES
    assert not has_does_not("Builds a design.\n\nIt writes nothing.")
    assert not has_does_not(None)
    assert has_does_not("Builds a design.\nDoes not write files.")
