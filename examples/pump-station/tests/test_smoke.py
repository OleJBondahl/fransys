"""Smoke test: fransys imports cleanly (STEP 1)."""

import fransys


def test_fransys_imports() -> None:
    assert fransys.__name__ == "fransys"
    assert callable(fransys.build)
    assert callable(fransys.write)
