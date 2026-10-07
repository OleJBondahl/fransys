"""Field case: a cable with one near end and three far ends lists every end.

The engineering shape: a 1:3 fan-out cable. Core 1 runs from a header J1 to J2, core 2 to J3
and core 3 to J4, so the cable has four ends.

The bug: the cable list row named the first two ends only and dropped J3 and J4 without a
finding. Fixed by decision model-0155 (ruling CD-H4): From is the first end, To lists every
other end in `cable_end_rank` order, joined by ", ".
"""

import fransys as fr
import pytest

from fransys_model.derive import cable_list_rows

_PLUG = "DEMO-CONN-4P"
_CABLE = "DEMO-CBL-4G1.5"


@pytest.fixture(scope="module")
def built() -> fr.BuildResult:
    """Loom W1 holding one cable, J1 on its near side and J2, J3, J4 on its far side."""
    d = fr.design("demo_parts")
    d.location("L0", "Workshop")
    with d.function("W1", "Loom W1"):
        loom = d.harness("W1", place="L0")
        near, *far = (
            d.device(tag, _PLUG, parent=loom, place="L0") for tag in ("J1", "J2", "J3", "J4")
        )
        cable = d.cable("W1", _CABLE, parent=loom, name="fan", place="L0")
        for core, end in enumerate(far, start=1):
            cable.core(core, near[core], end[core])
    return fr.build(d)


def test_the_cable_list_row_names_every_end(built: fr.BuildResult) -> None:
    """Every end's designation is in the row's From or To text."""
    (row,) = cable_list_rows(built.model)
    text = f"{row.from_label} {row.to_label}"
    for tag in ("J1", "J2", "J3", "J4"):
        assert f"-{tag}" in text
