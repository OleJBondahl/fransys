"""CONTENTS prints the shared `ContentsRow.ends` verbatim, never re-deriving it (model-0106,
pdf-0017). The appendix's own acceptance: a test that fails if `_contents.py` re-joins or
re-splits `ends` instead of reading it straight from the row `derive.contents_rows` returns.
"""

import fransys_pdf._contents as contents_module
from _build import (
    cable_facet,
    cable_product_facet,
    conductor,
    core_facet,
    document,
    item,
    model,
    part,
    pin,
)
from fransys_pdf._contents import contents_page

from fransys_model.derive.rows import ContentsRow
from fransys_model.vocab import ConductorKind, DocumentPreset, PageKind, documents

K = PageKind
_SENTINEL_ENDS = "P \N{EN DASH} Q"


def _one_cable_two_ends_contents_model():
    """A SYSTEM+CONTENTS document over one top-level cable `W1` with two real ends `M1`, `X3`."""
    cable_part = part("cab1", description="Invented 1-core cable")
    cable = item("w1", description="Cable one", part=cable_part.id)
    cf = cable_facet("w1", subject=cable.id, length_mm=1500)
    cpf = cable_product_facet("w1", subject=cable_part.id, core_count=1)
    m1_item, m1_fn, m1_port = pin("m1", "M1")
    x3_item, x3_fn, x3_port = pin("x3", "X3")
    core = conductor(
        "core-1", a=m1_port.id, b=x3_port.id, kind=ConductorKind.CORE, carrier=cable.id
    )
    core_marker = core_facet("core-1", subject=core.id, index=1)
    doc = document(
        "d1",
        preset=DocumentPreset.SYSTEM,
        cover="# Cover",
        notes=None,
        add=(K.CONTENTS,),
        remove=(K.HARNESS_DRAWING, K.CABLE_LIST, K.BOM),
    )
    m = model(
        cable_part,
        cable,
        cf,
        cpf,
        m1_item,
        m1_fn,
        m1_port,
        x3_item,
        x3_fn,
        x3_port,
        core,
        core_marker,
        doc,
    )
    return m, documents(m)[doc.id]


def _sentinel_rows(cables):
    """One `ContentsRow` per cable, `ends` replaced by a sentinel unrelated to the real ends."""
    return tuple(
        ContentsRow(
            cable=cable.cable,
            designation=cable.designation,
            mpn=cable.mpn,
            description=cable.description,
            core_count=cable.core_count,
            gauge_mm2=cable.gauge_mm2,
            length_mm=cable.length_mm,
            ends=_SENTINEL_ENDS,
        )
        for cable in cables
    )


def test_contents_page_prints_the_shared_row_s_ends_verbatim(monkeypatch):
    """The real ends are `-M1`/`-X3`; with `contents_rows` monkeypatched to a sentinel `ends`,
    the rendered table must show the sentinel, not the real designations -- proof that
    `_contents.py` reads `ContentsRow.ends` straight, never recomputing it from the raw cable.
    """
    m, record = _one_cable_two_ends_contents_model()
    monkeypatch.setattr(contents_module, "contents_rows", _sentinel_rows)
    text = contents_page(m, record, (K.CONTENTS,))
    assert f'text("{_SENTINEL_ENDS}")' in text
    assert "-M1" not in text
    assert "-X3" not in text
