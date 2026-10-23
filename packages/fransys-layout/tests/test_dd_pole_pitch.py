"""A multi-pole function with only some poles wired.

Same method as `test_dd_columns.py`: small invented designs on `examples/demo-parts`, read back
through the page Drawings of the core path and the findings of `fr.build`.
"""

from itertools import combinations

from dd_chain_fixtures import body_x, contactor_with_pole_one_wired, placed, terminal_tag

MAIN = ("-K1", "make-contact", 3)
TERMINAL = "terminal"


def test_a_multi_pole_function_with_only_pole_one_wired_stands_in_its_wired_poles_column() -> None:
    """D2: XA:1 - K1:main.1..2 - XB:1 is one column; K1's unwired poles 2 and 3 open no other."""
    # UNDO: _chain_walk.py `drop_unwired_poles`: the line that drops a single unwired non-terminal
    # pole's chain when its function has a pole in a longer chain (fails until that line exists)
    model = contactor_with_pole_one_wired(relays=False).model
    main = placed(model, *MAIN)
    above = placed(model, terminal_tag("XA", 1), TERMINAL)
    below = placed(model, terminal_tag("XB", 1), TERMINAL)
    assert above.x == main.x == below.x
    assert above.y < main.y < below.y
    in_column = [s for s in main.drawing.symbols if s.x == main.x]
    assert sorted((s.key, s.y) for s in in_column) == sorted(
        (p.symbol.key, p.y) for p in (above, main, below)
    )


def test_a_contactor_beside_two_relays_has_no_overlap_and_no_unplaced_label() -> None:
    """D2: K1 (pole 1 wired) beside K2, K3 (2CO): no keep-out shares interior, every label fits."""
    # UNDO: stages/chains.py: the `drop_unwired_poles` call removed AND place.py `_lane_offsets`:
    # `max(cell.lane * pitch, packed)` -> `cell.lane * pitch`; either alone still passes (the
    # next test guards the place.py change alone)
    result = contactor_with_pole_one_wired(relays=True)
    codes = [f.code for f in result.findings]
    assert "SYMBOL_OVERLAP" not in codes
    assert not {"LABEL_UNPLACED", "ANNEX_UNPLACED"} & set(codes)
    bodies = {
        tag: placed(result.model, tag, key, poles)
        for tag, key, poles in (
            MAIN,
            ("-K2", "operating-device", 1),
            ("-K3", "operating-device", 1),
        )
    }
    ranges = {tag: body_x(p) for tag, p in bodies.items()}
    same_page = [(a, b) for a, b in combinations(bodies, 2) if bodies[a].page == bodies[b].page]
    assert len(same_page) >= 1  # pages differ between bodies: only a shared page can overlap
    for a, b in same_page:
        (a0, a1), (b0, b1) = ranges[a], ranges[b]
        assert a1 <= b0 or b1 <= a0, f"{a} {ranges[a]} overlaps {b} {ranges[b]}"
