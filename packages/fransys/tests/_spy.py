"""A call-counting spy on a module function, for the pipeline gating tests."""

from typing import Any


def spy(monkeypatch, module, name):
    """Wrap `module.name` in a call-counting delegate to the real function."""
    calls: list[tuple[Any, ...]] = []
    original = getattr(module, name)

    def wrapper(*args, **kwargs):
        calls.append((args, kwargs))
        return original(*args, **kwargs)

    monkeypatch.setattr(module, name, wrapper)
    return calls
