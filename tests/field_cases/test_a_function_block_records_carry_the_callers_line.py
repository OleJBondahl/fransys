"""Field case: a record made inside a `with d.function(...)` block names the caller's file and line.
The bug: the block's group took its origin from `contextlib.py`, so a finding on it (GROUP_SPLIT) pointed into the standard library.
Fixed by the origin walk skipping `contextlib` frames, as for this package's own frames (invariant 1)."""

import fransys as fr


def _draft() -> fr.Design:
    d = fr.design("demo_parts")
    with d.function("A", "First"):
        lamp = d.device("H1", "DEMO-LAMP-24")
        d.device("H2", "DEMO-LAMP-24")
    with d.function("B", "Second"):
        d.device("H3", "DEMO-LAMP-24")
    d.series(lamp["1"], d.device("H4", "DEMO-LAMP-24")["1"], wire=("RD", 50))
    return d


def test_every_record_of_a_function_block_is_attributed_to_the_caller() -> None:
    draft = _draft().draft()
    origins = draft.origins()
    assert origins
    files = {origin.file for origin in origins.values()}
    assert files == {__file__}
