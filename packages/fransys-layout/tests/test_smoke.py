"""Smoke test: every layer imports, and so do the three dependencies on this interpreter."""

from fransys_layout import engines, geometry, lint, stages


def test_layers_import() -> None:
    """The four layers import cleanly."""
    assert geometry.__name__ == "fransys_layout.geometry"
    assert stages.__name__ == "fransys_layout.stages"
    assert lint.__name__ == "fransys_layout.lint"
    assert engines.__name__ == "fransys_layout.engines"


def test_symbol_libraries_load() -> None:
    """foundations.md 11, P2: the symbol libraries install and answer a lookup on Python 3.15."""
    from electrical_symbols import LIBRARY

    assert LIBRARY.get("make-contact").ports
