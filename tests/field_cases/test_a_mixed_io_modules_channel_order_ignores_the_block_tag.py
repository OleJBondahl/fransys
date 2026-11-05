"""Field case: a rack of mixed digital I/O modules whose input 1 and output 1 share channel number 1, inside one tagged unit block.
The bug: the DI/DO tie broke on the channel function's id, a hash of a key holding the block's tag, so renaming flipped directions.
Fixed by model-0259, a channel number orders by the part's function name, modules by `position=`, else by their own tag."""

import re
from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr

if TYPE_CHECKING:
    from pathlib import Path

_TAGS = ("AA", "ZZ", "M7", "B1")


class _Rack(NamedTuple):
    """A unit with no boundary device to hand back."""


def _cabinet(mpns: tuple[str, str], *, positions: bool):
    @fr.unit(
        "demo-cabinet",
        revision=1,
        interface_version=1,
        date="2026-10-02",
        text="First release",
        by="XX",
    )
    def cabinet(d: fr.Design) -> _Rack:
        """A rack item with two PLC modules under it."""
        rack = d.device("A1", "DEMO-PCB-IO", name="rack")
        for index, mpn in enumerate(mpns, start=1):
            extra: dict[str, Any] = {"position": index} if positions else {}
            d.device(f"A{index + 1}", mpn, parent=rack, name=f"m{index}", **extra)
        return _Rack()

    return cabinet


def _exports(tag: str, tmp_path: Path, *, mpns: tuple[str, str], positions: bool) -> dict[str, str]:
    """plc.csv and the Wago XML of one build, the block tag replaced by `@` in their text."""
    d = fr.design("demo_parts")
    d.add(_cabinet(mpns, positions=positions), tag)
    written = fr.write(fr.build(d), tmp_path / tag)
    found = {"csv": "", "xml": ""}
    for path in written:
        if path.name.endswith("plc.csv"):
            found["csv"] = path.read_text(encoding="utf-8").replace(tag, "@")
        elif path.name.endswith(".xml") and "wago" in path.name:
            found["xml"] = path.read_text(encoding="utf-8").replace(tag, "@")
    return found


def test_the_direction_of_each_channel_does_not_change_with_the_block_tag(tmp_path: Path) -> None:
    """Same design, only the block tag changed: the same plc.csv and Wago XML text."""
    mpns = ("DEMO-PLC-DIO-1", "DEMO-PLC-DIO-1")
    texts = [_exports(tag, tmp_path, mpns=mpns, positions=True) for tag in _TAGS]
    assert all(text["csv"] and text["xml"] for text in texts)
    assert all(text == texts[0] for text in texts)


def _module_order(text: str) -> list[str]:
    """The module designations in the order the plc.csv rows first name them."""
    return list(dict.fromkeys(re.findall(r"^-@-(A\d):", text, re.MULTILINE)))


def test_renaming_the_block_does_not_swap_modules_without_a_position(tmp_path: Path) -> None:
    """Without `position=`, the modules keep their order when only the block tag changes."""
    mpns = ("DEMO-PLC-DO-2", "DEMO-PLC-DI-2")
    orders = [_module_order(_exports(tag, tmp_path, mpns=mpns, positions=False)["csv"]) for tag in _TAGS]
    assert orders[0] == ["A2", "A3"]
    assert all(order == orders[0] for order in orders)
