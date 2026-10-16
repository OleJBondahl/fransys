"""Field case: a document's cable list names the cables its drawings draw, no others.

The engineering shape: a workshop with a mixed loom (a harness holding its own cable) and a loose
cable between two plugs that belong to no harness. One document is made for the workshop
location, one for the loom.

The bug: the location document draws no cable, yet its cable list named every top-level cable;
the loom document drew its own cable, yet its list named the loose one as well. The list and the
drawings disagreed about the document's scope.

The rule (decision pdf-0042, owner 2026-10-16): a document's lists cover exactly what its
drawings draw. A location document's cable list is empty, so its page is left out
(`DOCUMENT_EMPTY_LIST`); the loom document's list names the loom's cable only.
"""

import tempfile
from functools import cache
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
import fransys_pdf
import fransys_render

from fransys_model.derive import document_sheets_of
from fransys_model.vocab.tables import documents


@cache
def _built() -> tuple[fr.BuildResult, dict[str, str]]:
    d = fr.design("demo_parts")
    workshop = d.location("L0", "Workshop")
    with d.function("MIX", "Mixed loom"):
        loom = d.harness("MIX", place="L0")
        near = d.device("J1", "DEMO-CONN-4P", parent=loom, place="L0")
        far = d.device("J2", "DEMO-CONN-4P", parent=loom, place="L0")
        d.cable("MIX", "DEMO-CBL-4G1.5", parent=loom, name="cmix", place="L0").core(
            1, near[1], far[1]
        )
    with d.function("LOOSE", "Loose"):
        a = d.device("LA1", "DEMO-CONN-2P", place="L0")
        b = d.device("LA2", "DEMO-CONN-2P", place="L0")
        d.cable("W2", "DEMO-CBL-4G1.5", place="L0").core(1, a[1], b[1])
    with tempfile.TemporaryDirectory() as tmp:
        cover = Path(tmp) / "cover.md"
        cover.write_text("# Cover\n", encoding="utf-8")
        add, remove = (fr.PageKind.CABLE_LIST,), (fr.PageKind.BOM,)
        built = fr.build(
            d,
            fr.document(
                fr.DocumentPreset.CABINET_SCHEMATIC, workshop, cover=cover, add=add, remove=remove
            ),
            fr.document(
                fr.DocumentPreset.HARNESS_DRAWING, loom, cover=cover, add=add, remove=remove
            ),
        )
    texts = {
        str(record.preset): fransys_pdf.source(
            built.model, doc_id, {}, fransys_render.sheets(document_sheets_of(built.model))
        )
        for doc_id, record in documents(built.model).items()
    }
    return built, texts


def _empty_cable_lists() -> int:
    model = _built()[0].model
    return sum(
        1
        for f in fransys_pdf.check(model, {})
        if f.code == "DOCUMENT_EMPTY_LIST" and "CABLE_LIST" in f.message
    )


def test_the_loom_document_lists_its_own_cable_and_not_the_loose_one() -> None:
    """The loom's drawings draw `-MIX` only, so its cable list names `-MIX` and not `-W2`."""
    text = _built()[1]["DocumentPreset.HARNESS_DRAWING"]
    assert 'text("-MIX")' in text
    assert "-W2" not in text


def test_the_location_document_cable_list_names_no_cable() -> None:
    """The location document draws no cable: its list is empty, the page left out."""
    text = _built()[1]["DocumentPreset.CABINET_SCHEMATIC"]
    assert "-W2" not in text
    assert 'text("-MIX")' not in text
    assert _empty_cable_lists() == 1


class _Opened(NamedTuple):
    loom: Any


@fr.unit("demo-loom", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _loom_unit(u: Any) -> _Opened:
    loom = u.harness("MIX")
    near = u.device("J1", "DEMO-CONN-4P", parent=loom, name="n")
    far = u.device("J2", "DEMO-CONN-4P", parent=loom, name="f")
    u.cable("MIX", "DEMO-CBL-4G1.5", parent=loom, name="cmix").core(1, near[1], far[1])
    return _Opened(loom)


@cache
def _unit_loom_text() -> str:
    """The item document of a harness that is a member of a unit; its cable has that unit."""
    d = fr.design("demo_parts")
    d.location("CAB", "Cabinet")
    unit = d.add(_loom_unit, "U1", place="CAB")
    with tempfile.TemporaryDirectory() as tmp:
        cover = Path(tmp) / "cover.md"
        cover.write_text("# Cover\n", encoding="utf-8")
        add, remove = (fr.PageKind.CABLE_LIST,), (fr.PageKind.BOM,)
        doc = fr.document(
            fr.DocumentPreset.HARNESS_DRAWING, unit.loom, cover=cover, add=add, remove=remove
        )
        built = fr.build(d, doc)
    (doc_id,) = documents(built.model)
    return fransys_pdf.source(
        built.model, doc_id, {}, fransys_render.sheets(document_sheets_of(built.model))
    )


def test_a_unit_members_loom_document_lists_the_cable_it_draws() -> None:
    """The loom sits in a unit, so its cable has that unit; the item document draws it anyway."""
    assert 'text("-MIX")' in _unit_loom_text()
