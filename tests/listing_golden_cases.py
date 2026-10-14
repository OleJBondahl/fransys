"""The listing golden cases (LISTING-STABILITY LS1): built here, compared by `test_listing_golden`.

Run `uv run python tests/listing_golden_cases.py` (or `just regen-goldens listing`) to rewrite
`tests/golden/listing/`. A golden moves only with a `listing_version` bump and a release-note line.
Demo parts only; the demo cabinet and board are `test_baseline_listing`'s own builders.
"""

import sys
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
import fransys_parts
from fransys.colours import BK, GNYE

from fransys_model.derive import baseline
from fransys_model.vocab.tables import units

GOLDEN_DIR = Path(__file__).resolve().parent / "golden" / "listing"
_TESTS = Path(__file__).resolve().parent


class _Io(NamedTuple):
    X7: fr.Device


class _Open(NamedTuple):
    pass


@fr.unit("lg-board", revision=1, interface_version=1, date="2026-10-14", text="first", by="AB")
def _board(u: Any) -> _Io:
    """The nested unit: a boundary connector `X7` wired to a lamp."""
    pcb = u.device("A1", "DEMO-PCB-IO")
    x7 = u.device("X7", "DEMO-HSG-4F", parent=pcb, interface=True, contacts="DEMO-CRIMP-F")
    lamp = u.device("H1", "DEMO-LAMP-24", parent=pcb)
    u.wire(x7[1], lamp["1"], wire=(BK, 0.5))
    u.wire(x7[2], lamp["2"], wire=(BK, 0.5))
    return _Io(x7)


@fr.unit("lg-cabinet", revision=1, interface_version=1, date="2026-10-14", text="first", by="AB")
def _cabinet(u: Any) -> _Open:
    """Every moving text rule at once: bar, loom, tagged instance, head and block, strip, mate."""
    board = u.add(_board, "U1")
    pe1 = u.device("PE1", "DEMO-PEBAR-20").pe
    for name in ("M1", "M2"):
        u.wire(u.device(name, "DEMO-MOTOR-4KW").motor["PE"], pe1, wire=(GNYE, 2.5))
    with u.function("W5", "Loom"):
        loom = u.harness("W5")
        plug = u.device("P5", "DEMO-HSG-4M", parent=loom, contacts="DEMO-CRIMP-M")
        far = u.device("P6", "DEMO-CONN-2P", parent=loom)
        u.cable("W5", "DEMO-CBL-4G1.5", parent=loom, name="cable").core(1, plug[3], far[1])
    u.mate(plug, board.X7)
    u.net("LAMP", far[2], board.X7[3])
    strip = u.terminal_strip("X1", "DEMO-TB-2.5")
    head = u.device("S1", "DEMO-HEAD-ESTOP")
    block = u.device(None, "DEMO-BLOCK-1NC", name="block-1", parent=head)
    u.wire(strip[1], block["11"], wire=(BK, 0.5))
    u.wire(block["12"], strip[2], wire=(BK, 0.5))
    return _Open()


def _all_moves() -> Any:
    d = fr.design("demo_parts")
    d.project(title="Listing", number="LG-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-14", text="First issue", created="XX")
    d.location("CAB", "Cabinet")
    d.add(_cabinet, "C1", place="CAB")
    return fr.build(d).model


def _demo_models() -> dict[str, Any]:
    """The baseline spec's worked example: `demo-pump-cabinet` nesting one `demo-io-board`."""
    sys.path.append(str(_TESTS))
    from test_baseline_listing import _board, _cabinet, _new_design

    parts = fransys_parts.load("demo_parts")
    board = _new_design(parts)
    _board(board.scope("brd"))
    cabinet = _new_design(parts)
    _cabinet(cabinet.scope("cab"))
    return {
        "board": fr.build(parts, board.draft()).model,
        "cabinet": fr.build(parts, cabinet.draft()).model,
    }


def cases() -> dict[str, str]:
    """Golden file name -> the canonical listing text, system first, then each unit."""
    out: dict[str, str] = {}
    models = {**_demo_models(), "all_moves": _all_moves()}
    for stem, model in models.items():
        out[f"{stem}.system.json"] = baseline.dumps(baseline.listing(model, None))
        for unit_id, unit in sorted(units(model).items(), key=lambda kv: kv[1].key):
            name = "-".join(unit.key)
            out[f"{stem}.{name}.json"] = baseline.dumps(baseline.listing(model, unit_id))
    return out


def main() -> None:
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    for old in GOLDEN_DIR.glob("*.json"):
        old.unlink()
    for name, text in cases().items():
        (GOLDEN_DIR / name).write_bytes(text.encode("utf-8"))


if __name__ == "__main__":
    main()
