"""Field case: the members a `PAGE_UNDERFILLED` message lists do not change under a rename.

Engineering shape: a cabinet page holds four lamps P1, P2, P10 and P11, each wired to a terminal
of one strip, declared out of order. The page is nearly empty, so it draws one finding, whose
message ends in the page and the first four of its members' designations ("and N more").

The bug: the members came in `Id` order, so a rename of the `name=` keys changed which four were
shown, and in which order.

Fixing decision: 0135 (the members list by `natural_key` of their designations).
"""

import re
from typing import TYPE_CHECKING

import fransys as fr
import pytest

if TYPE_CHECKING:
    from pathlib import Path

_SALTS = ("a", "m", "z", "q", "k")


def _members(salt: str, tmp_path: Path) -> list[str]:
    d = fr.design("demo_parts", place="C1")
    cabinet = d.location("C1", "Cabinet")
    strip = d.terminal_strip("X1", "DEMO-TB-2.5", 12, name=f"{salt}x1")
    for n in (10, 1, 11, 2):
        lamp = d.device(f"P{n}", "DEMO-LAMP-24", name=f"{salt}p{n}")
        d.wire(strip[n].inner, lamp.lamp["1"], wire=("WH", 0.75))
    (tmp_path / "c.md").write_text("# Cabinet\n", encoding="utf-8")
    document = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cabinet, cover=tmp_path / "c.md")
    (found,) = [f for f in fr.build(d, document).findings if f.code == "PAGE_UNDERFILLED"]
    match = re.search(r"\+C1p1: (.+)\)$", found.message)
    assert match
    return match.group(1).split(", ")


@pytest.mark.parametrize("salt", _SALTS)
def test_the_listed_members_are_in_natural_order(salt: str, tmp_path: Path) -> None:
    shown = [m for m in _members(salt, tmp_path) if not m.startswith("and ")]
    keys = [fr.derive.natural_key(m) for m in shown]
    assert len(shown) == 4
    assert keys == sorted(keys)


def test_a_rename_leaves_the_listed_members_unchanged(tmp_path: Path) -> None:
    assert len({tuple(_members(salt, tmp_path)) for salt in _SALTS}) == 1
