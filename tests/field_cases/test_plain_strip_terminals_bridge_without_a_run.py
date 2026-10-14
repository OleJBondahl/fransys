"""Field case: adjacent terminals of a plain strip bridge without a run.

The engineering shape: a feed strip X4 of six terminals carries one common supply to the
terminals 2 to 6, each jumpered to the next, with no named run of its own.

The bug: a strip could not bridge its terminals; only a run could, and a run prints its label in
every designation (-X4:24V:2). The shape the consumer wanted, a plain strip with -X4:2 to -X4:6
and one jumper group, could not be written.
Fixing decision: author-0038 (a strip's `bridged=` jumps adjacent terminals as a run's bridge
does, with no run).
"""

import fransys as fr

from fransys_model.vocab.tables import items


def _x4_rows() -> list:
    d = fr.design("demo_parts")
    d.terminal_strip("X4", "DEMO-TB-2.5", 6, bridged=(2, 6))
    model = fr.build(d).model
    strip = next(i for i, item in items(model).items() if item.key[-1] == "X4")
    return list(fr.derive.terminal_rows(model, strip))


def test_plain_strip_terminals_bridge_without_a_run() -> None:
    """Terminals 2 to 6 print with their designations and share one jumper group."""
    rows = _x4_rows()
    by_index = {row.index: row for row in rows}
    assert [by_index[i].designation for i in range(2, 7)] == [
        "-X4:2",
        "-X4:3",
        "-X4:4",
        "-X4:5",
        "-X4:6",
    ]
    groups = {by_index[i].jumper_group for i in range(2, 7)}
    assert len(groups) == 1
    assert None not in groups
    assert by_index[1].jumper_group is None
