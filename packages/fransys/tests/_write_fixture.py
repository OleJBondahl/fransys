"""Script for `test_write_across_processes`: build and write a system and a cabinet document.

Run as `python _write_fixture.py WORK_DIR`: builds two harnesses of `demo_parts` (each a
cable of two cores between two connectors), a `SYSTEM` document and a cabinet document.
"""

import sys
from pathlib import Path

import fransys as fr
from fransys import DocumentPreset
from fransys_author.design import Design


def main(work: Path) -> None:
    """Build the fixture and write both trees under `work`."""
    parts = fr.parts("demo_parts")
    d = Design(parts)
    d.project(title="Demo harnesses", number="DEMO-3", customer="Demo Co", revision=1, author="d")
    d.revision(1, date="2026-09-22", text="First issue", created="XX")
    c1 = d.location("C1", "Demo cabinet")
    sup = d.group("SUP", "Supply")
    for n in (1, 2):
        housing = d.item("DEMO-CONN-2P", tag=f"X{n}0", at=c1, group=sup)
        loose = d.item("DEMO-CONN-2P", tag=f"X{n}1", at=c1, group=sup)
        cable = d.cable("DEMO-CBL-4G1.5", tag=f"W{n}", at=c1)
        cable.core(1, housing.fn("x1")["1"], loose.fn("x1")["1"])
        cable.core(2, housing.fn("x1")["2"], loose.fn("x1")["2"])

    covers = work / "cover"
    covers.mkdir(parents=True)
    cover = covers / "system.md"
    cover.write_text("# System\n", encoding="utf-8")
    system = fr.document(DocumentPreset.SYSTEM, None, cover=cover)
    cover = covers / "cabinet.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    cabinet = fr.document(DocumentPreset.CABINET_SCHEMATIC, c1, cover=cover)
    result = fr.build(parts, d.draft(), system, cabinet)
    fr.write(result, work / "out", intermediates=work / "intermediates")
    # Positive control for the test: proves the child really ran under its own hash seed.
    (work / "hash-of-a-str.txt").write_text(str(hash("fransys")), encoding="utf-8")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
