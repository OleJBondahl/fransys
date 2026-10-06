"""Field case: a unit whose only item is one plain device, released, then given another part.

The bug: a sole root item of a unit has the designation `""` in the baseline listing, because
its designation is a fact of the instance and the parent names the instance (baseline spec L2,
board black-box B3). `fr.diff` printed that row's subject as the empty string, so the change
note read "Changed : mpn ..." and named nothing.

Reproduced 2026-10-05. Fixed by decision model-0132: a `Change` on a `""` row names the unit
itself, `<unit name> <version>.<revision>`; listings and stored baselines do not move.
"""

from typing import TYPE_CHECKING, NamedTuple

import fransys as fr

if TYPE_CHECKING:
    from pathlib import Path


class _Open(NamedTuple):
    """A unit with no boundary device to hand back."""


_NAME = "lone"


def _build(part: str) -> fr.BuildResult:
    """A unit whose single item is `part`, authored with no tag, group or parent."""

    @fr.unit(_NAME, revision=1, interface_version=1, date="2026-10-05", text="First issue", by="XX")
    def lone(u: fr.Design) -> _Open:
        u.device("lamp", part)
        return _Open()

    d = fr.design("demo_parts")
    d.add(lone, "U1")
    return fr.build(d)


def test_sole_device_unit_diff_names_the_unit(tmp_path: Path) -> None:
    """Changing the part of a lone device gives a diff line that names the unit, never `""`."""
    baselines = tmp_path / "baselines"
    first = _build("DEMO-LAMP-24")
    fr.release(first, baselines, unit=_NAME)
    text = fr.diff(_build("DEMO-CONN-2P"), baselines, unit=_NAME)
    assert "- Changed ``" not in text
    assert f"- Changed `{_NAME} 1.1`: mpn DEMO-LAMP-24 to DEMO-CONN-2P." in text
