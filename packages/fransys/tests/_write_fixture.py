"""Script for `test_write_across_processes`: build and write two harness documents.

Run as `python _write_fixture.py WORK_DIR`: builds two harnesses of `demo_parts` (each a
cable of two cores between two connectors), a `HARNESS_DRAWING` document per harness (PDF
pages and their cable table pages, no schematic, no SVG, CT1/CT2), and writes `WORK_DIR/out`
and `WORK_DIR/intermediates`. It imports only the facade, so a fresh interpreter needs nothing
from pytest.
"""

import sys
from pathlib import Path

import fransys as fr
import fransys_author
from fransys import DocumentPreset, PageKind


def main(work: Path) -> None:
    """Build the fixture and write both trees under `work`."""
    parts = fr.parts("demo_parts")
    d = fransys_author.Design(parts)
    d.project(title="Demo harnesses", number="DEMO-3", customer="Demo Co", revision=1, author="d")
    d.revision(1, date="2026-09-22", text="First issue", created="XX")
    c1 = d.location("C1", "Demo cabinet")
    sup = d.group("SUP", "Supply")
    harnesses = []
    for n in (1, 2):
        harness = d.harness(tag=f"WH{n}", at=c1, group=sup)
        housing = d.item("DEMO-CONN-2P", tag=f"X{n}0", parent=harness, at=c1, group=sup)
        loose = d.item("DEMO-CONN-2P", tag=f"X{n}1", at=c1, group=sup)
        cable = d.cable("DEMO-CBL-4G1.5", tag=f"W{n}", parent=harness, at=c1)
        cable.core(1, housing.fn("x1")["1"], loose.fn("x1")["1"])
        cable.core(2, housing.fn("x1")["2"], loose.fn("x1")["2"])
        d.mate(housing, loose)
        harnesses.append(harness)

    covers = work / "cover"
    covers.mkdir(parents=True)
    documents = []
    for n, harness in enumerate(harnesses, start=1):
        cover = covers / f"harness{n}.md"
        cover.write_text(f"# Harness {n}\n", encoding="utf-8")
        documents.append(
            fr.document(
                DocumentPreset.HARNESS_DRAWING, harness, cover=cover, remove=(PageKind.SCHEMATIC,)
            )
        )
    cover = covers / "cabinet.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    cabinet = fr.document(
        DocumentPreset.CABINET_SCHEMATIC,
        c1,
        cover=cover,
        remove=(PageKind.PLC_LIST, PageKind.TERMINAL_LIST, PageKind.BOM),
    )
    result = fr.build(parts, d.draft(), *documents, cabinet)
    fr.write(result, work / "out", intermediates=work / "intermediates")
    # Positive control for the test: proves the child really ran under its own hash seed.
    (work / "hash-of-a-str.txt").write_text(str(hash("fransys")), encoding="utf-8")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
