"""`SymdefError` and `Library` are the package's re-exports of symdef's, with their docstrings."""

import symdef

import electrical_symbols as es


def test_the_two_names_are_symdefs_own_and_on_the_surface():
    assert es.SymdefError is symdef.SymdefError
    assert es.Library is symdef.Library
    assert {"SymdefError", "Library"} <= set(es.__all__)


def test_each_has_a_docstring_within_the_surface_limit():
    for name in ("SymdefError", "Library"):
        doc = getattr(es, name).__doc__
        assert doc
        assert len(doc.strip().splitlines()) <= 15


def test_the_bundled_library_is_a_library():
    assert isinstance(es.LIBRARY, es.Library)
    assert issubclass(symdef.InvalidValueError, es.SymdefError)
