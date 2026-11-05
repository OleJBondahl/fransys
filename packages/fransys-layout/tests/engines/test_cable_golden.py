"""The cable engine's golden: every placed cable block of the invented models.

One file, `tests/golden/cable_blocks.txt`, holds for each model and each (reading, subject) either
`no block` or the block's head, boxes, end boxes and wires, as `lay_out_cables` places them. It
"""

from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Any

import pytest
from cable_models import MODELS

from fransys_layout.engines.cable.read.subjects import block_pairs
from fransys_model.derive.cable_drawing import cable_block_key
from fransys_model.kernel import Id, Model
lazy from fransys_layout import CableLayout

_GOLDEN = Path(__file__).resolve().parent.parent / "golden" / "cable_blocks.txt"


@pytest.fixture
def regenerate(request: pytest.FixtureRequest) -> bool:
    """True under `--regenerate-golden`: the golden is rewritten instead of compared."""
    return bool(request.config.getoption("--regenerate-golden"))


def _name(model: Model, found: Id[Any]) -> str:
    record = model.tables[found.kind].get(found)
    return "/".join(record.key) if record is not None else found.value


def _show(model: Model, value: Any) -> str:
    if isinstance(value, Id):
        return _name(model, value)
    if isinstance(value, tuple):
        return "[" + " ".join(_show(model, v) for v in value) + "]"
    if is_dataclass(value):
        inner = ",".join(f"{f.name}={_show(model, getattr(value, f.name))}" for f in fields(value))
        return f"{type(value).__name__}({inner})"
    return str(value)


def _is_part(value: Any) -> bool:
    if isinstance(value, Id):
        return False
    if isinstance(value, tuple):
        return bool(value) and all(is_dataclass(v) for v in value)
    return bool(is_dataclass(value))


def _block_lines(model: Model, block: Any) -> list[str]:
    """The block's scalar fields on one line, then each part of a part field on its own."""
    named = [(f.name, getattr(block, f.name)) for f in fields(block)]
    scalars = " ".join(f"{n}={_show(model, v)}" for n, v in named if not _is_part(v))
    lines = [f"  {type(block).__name__} {scalars}"]
    for name, found in named:
        if _is_part(found):
            ones = found if isinstance(found, tuple) else (found,)
            lines.extend(f"    {name}: {_show(model, one)}" for one in ones)
    return lines


def _dump(model: Model, laid: CableLayout) -> list[str]:
    blocks = laid.blocks
    lines: list[str] = []
    for unit, subject in block_pairs(model):
        where = "absolute" if unit is None else "unit " + _name(model, unit)
        lines.append(f"{_name(model, subject)} [{where}]")
        block = blocks.get(cable_block_key(unit, subject))
        lines += _block_lines(model, block) if block else ["  no block"]
    return lines


def golden_text() -> str:
    """The golden's text: each model's name, then its blocks."""
    out: list[str] = []
    for name, build in MODELS.items():
        built = build()
        out += [f"== {name}", *_dump(built.frozen, built.layout)]
    return "\n".join(out) + "\n"


def test_cable_blocks_match_the_golden(*, regenerate: bool) -> None:
    """Any change to a drawn cable block, or to which cables draw, moves this file.

    Probe: a patch to `engines/cable/place.py::_core_wire` shifting one wire's run by one grid unit.
    """
    actual = golden_text()
    if regenerate:
        _GOLDEN.write_text(actual, encoding="utf-8", newline="\n")
    assert actual == _GOLDEN.read_text(encoding="utf-8")
