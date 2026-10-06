"""Smoke test: subpackages import and builtin frozendict works."""

from fransys_model import derive, kernel, vocab


def test_import_and_frozendict() -> None:
    """Subpackages import cleanly and the builtin frozendict works."""
    assert kernel.__name__ == "fransys_model.kernel"
    assert vocab.__name__ == "fransys_model.vocab"
    assert derive.__name__ == "fransys_model.derive"
    assert frozendict({"a": 1})["a"] == 1
