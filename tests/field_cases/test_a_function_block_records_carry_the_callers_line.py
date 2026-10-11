"""Field case: a record made by a `with d.function(...)` block names the caller's file and line.

The engineering shape: a circuit opens a function block, makes a device inside it and wires
two of its pins, then makes a second block. Every record the block creates, the function's
group included, is authored at a line of the user's module.

The bug: the group the block makes took its origin from `contextlib.py`, the first frame
outside `fransys_author` on the stack, so a finding on it (`GROUP_SPLIT`) pointed into the
standard library. Invariant 1: every record carries its Origin. Fixed by the origin walk
skipping `contextlib` frames as it does this package's own.
"""

import fransys as fr


def _draft() -> fr.Design:
    d = fr.design("demo_parts")
    with d.function("A", "First"):
        lamp = d.device("H1", "DEMO-LAMP-24")
        d.device("H2", "DEMO-LAMP-24")
    with d.function("B", "Second"):
        d.device("H3", "DEMO-LAMP-24")
    d.wire(lamp["1"], d.device("H4", "DEMO-LAMP-24")["1"], wire=("RD", 50))
    return d


def test_every_record_of_a_function_block_is_attributed_to_the_caller() -> None:
    draft = _draft().draft()
    origins = draft.origins()
    assert origins
    files = {origin.file for origin in origins.values()}
    assert files == {__file__}
