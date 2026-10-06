"""The cable table page's own pieces: heading line, "by others" note and per-core table (cable
tables spec CT2-CT4, `docs/archive/specs/2026-09-27-cable-tables.md`).

`_part_line` and `_cable_table` are pure over a bare `HarnessCable`/`HarnessCore`, so
most tests below build one by hand, `test_signed_scope.py`'s own pattern -- no model at all.
`_cable_external_note` calls `derive.external`, which resolves its argument against a real
model, so its tests build one with `_build`'s helpers plus `dataclasses.replace(item(...),
external=True)` (`_build.item` takes no `external` keyword, `test_signed_scope.py`'s own
`replace(location(...), parent=...)` pattern for the same reason).
"""

from dataclasses import replace
from decimal import Decimal

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
from fransys_pdf import source
from fransys_pdf._drawings import (
    _cable_external_note,
    _cable_heading,
    _cable_table,
    _part_line,
    harness_cables_for,
)
from fransys_pdf._typst import literal

from fransys_model.derive import HarnessCable, HarnessCore, HarnessEnd
from fransys_model.kernel import make_id
from fransys_model.vocab import (
    Conductor,
    ConductorKind,
    DocumentPreset,
    PageKind,
    Port,
    documents,
)

K = PageKind


def _cable(  # noqa: PLR0913 -- one keyword per `HarnessCable` field under test, as `_build`'s own helpers do
    *,
    designation: str = "-W1",
    mpn: str | None = None,
    description: str | None = None,
    core_count: int | None = None,
    gauge_mm2: Decimal | None = None,
    length_mm: int | None = None,
    cores: tuple[HarnessCore, ...] = (),
    ends: tuple[HarnessEnd, ...] = (),
) -> HarnessCable:
    """A bare `HarnessCable`, `designation` real and every other field left to its keyword."""
    return HarnessCable(
        cable=item("cable-under-test", description="Cable one").id,
        designation=designation,
        mpn=mpn,
        description=description,
        core_count=core_count,
        gauge_mm2=gauge_mm2,
        shielded=None,
        length_mm=length_mm,
        cores=cores,
        ends=ends,
    )


def _core(
    *, index: int, end_a_designation: str, end_b_designation: str, label: str | None
) -> HarnessCore:
    """A bare `HarnessCore` with dummy conductor/port ids -- `_cable_table` never resolves
    them against a model, so they need not be real.
    """
    return HarnessCore(
        conductor=make_id(Conductor, ("conductor", f"c{index}")),
        index=index,
        colour="black",
        label=label,
        end_a=make_id(Port, ("port", f"a{index}")),
        end_a_designation=end_a_designation,
        end_b=make_id(Port, ("port", f"b{index}")),
        end_b_designation=end_b_designation,
    )


# -- `_part_line` (pdf-0021) ------------------------------------------------------------------


def test_part_line_is_empty_when_every_field_is_none():
    """Every optional field unset: no text, no separators."""
    assert _part_line(_cable(designation="-W1")) == ""


def test_part_line_joins_mpn_description_and_the_composite():
    """The order is mpn, description, the core/gauge composite; the designation and the
    length are not part of it.
    """
    cable = _cable(
        designation="-W1",
        mpn="ACME-1",
        description="A cable",
        core_count=4,
        gauge_mm2=Decimal("1.5"),
        length_mm=1500,
    )
    assert _part_line(cable) == "ACME-1, A cable, 4 x 1.5 mm²"


def test_part_line_omits_the_composite_when_only_core_count_is_set():
    """`core_count` and `gauge_mm2` are one field: `gauge_mm2=None` drops the whole composite,
    proving it is not printed from `core_count` alone.
    """
    cable = _cable(designation="-W1", mpn="ACME-1", core_count=4, gauge_mm2=None)
    assert _part_line(cable) == "ACME-1"


def test_part_line_omits_the_composite_when_only_gauge_is_set():
    """The other half of the same proof: `core_count=None` alone also drops the composite."""
    cable = _cable(designation="-W1", mpn="ACME-1", core_count=None, gauge_mm2=Decimal("1.5"))
    assert _part_line(cable) == "ACME-1"


def test_part_line_omits_mpn_and_description_when_falsy():
    """`mpn=""` and `description=None` are both falsy and drop like `None`."""
    cable = _cable(designation="-W1", mpn="", description=None, core_count=2, gauge_mm2=Decimal(1))
    assert _part_line(cable) == "2 x 1 mm²"


# -- `_cable_external_note` (Y3) -------------------------------------------------------------


def test_cable_external_note_is_none_off_the_system_preset():
    """Y3's own gate: even a genuinely external cable prints no note on a non-SYSTEM document."""
    cable_item = replace(item("w1", description="Cable one"), external=True)
    doc = document("d1", preset=DocumentPreset.HARNESS_DRAWING, subject=cable_item, cover="# Cover")
    m = model(cable_item, doc)
    record = documents(m)[doc.id]
    cable = HarnessCable(
        cable=cable_item.id,
        designation="-W1",
        mpn=None,
        description=None,
        core_count=None,
        gauge_mm2=None,
        shielded=None,
        length_mm=None,
        cores=(),
        ends=(),
    )
    assert _cable_external_note(m, record, cable) is None


def test_cable_external_note_is_none_on_system_when_nothing_is_covered():
    """A SYSTEM document with a non-external cable and no ends: nothing to cover, `None`."""
    cable_item = item("w2", description="Cable two")
    doc = document("d2", preset=DocumentPreset.SYSTEM, cover="# Cover")
    m = model(cable_item, doc)
    record = documents(m)[doc.id]
    cable = HarnessCable(
        cable=cable_item.id,
        designation="-W1",
        mpn=None,
        description=None,
        core_count=None,
        gauge_mm2=None,
        shielded=None,
        length_mm=None,
        cores=(),
        ends=(),
    )
    assert _cable_external_note(m, record, cable) is None


def test_cable_external_note_covers_the_cable_before_its_external_end():
    """The cable's own designation is covered first, then its ends in `cable.ends` order --
    the exact two-part string, cable before end.
    """
    cable_item = replace(item("w3", description="Cable three"), external=True)
    end_item = replace(item("x3", description="Connector"), external=True)
    doc = document("d3", preset=DocumentPreset.SYSTEM, cover="# Cover")
    m = model(cable_item, end_item, doc)
    record = documents(m)[doc.id]
    end = HarnessEnd(
        item=end_item.id,
        designation="-X1",
        connector=None,
        style=None,
        pincount=None,
        gender=None,
        mpn=None,
        pins=(),
    )
    cable = HarnessCable(
        cable=cable_item.id,
        designation="-W1",
        mpn=None,
        description=None,
        core_count=None,
        gauge_mm2=None,
        shielded=None,
        length_mm=None,
        cores=(),
        ends=(end,),
    )
    assert _cable_external_note(m, record, cable) == "by others: -W1, -X1"


def test_cable_external_note_never_covers_a_blank_designation_end():
    """An end whose `designation` is `""` is never covered, even though its item is external:
    `end.designation and external(model, end.item)` short-circuits on the blank string first.
    """
    cable_item = item("w4", description="Cable four")
    end_item = replace(item("x4", description="Connector"), external=True)
    doc = document("d4", preset=DocumentPreset.SYSTEM, cover="# Cover")
    m = model(cable_item, end_item, doc)
    record = documents(m)[doc.id]
    end = HarnessEnd(
        item=end_item.id,
        designation="",
        connector=None,
        style=None,
        pincount=None,
        gender=None,
        mpn=None,
        pins=(),
    )
    cable = HarnessCable(
        cable=cable_item.id,
        designation="-W1",
        mpn=None,
        description=None,
        core_count=None,
        gauge_mm2=None,
        shielded=None,
        length_mm=None,
        cores=(),
        ends=(end,),
    )
    assert _cable_external_note(m, record, cable) is None


# -- `_cable_table` (CT2, CT4) ----------------------------------------------------------------


def test_cable_table_is_header_only_for_a_zero_core_cable():
    """CT4: a zero-core cable gets the same 4-column header, strong for each label, no data
    row at all.
    """
    headers = ("Core", "From", "To", "Label")
    header_cells = ", ".join(f"strong(text({literal(h)}))" for h in headers)
    expected = f"#table(columns: 4, stroke: 0.5pt, table.header({header_cells}))"
    assert _cable_table(_cable(cores=())) == expected


def test_cable_table_prints_one_row_per_core_with_a_blank_label_as_empty_text():
    """One row per core, the four columns in order (`index`, `end_a_designation`,
    `end_b_designation`, `label`); a `None` label prints `""` via `text("")`.
    """
    core1 = _core(index=1, end_a_designation="-X1:1", end_b_designation="-X2:1", label="L1")
    core2 = _core(index=2, end_a_designation="-X1:2", end_b_designation="-X2:2", label=None)
    text = _cable_table(_cable(cores=(core1, core2)))
    row1 = (
        f"text({literal('1')}), text({literal('-X1:1')}), "
        f"text({literal('-X2:1')}), text({literal('L1')})"
    )
    row2 = (
        f"text({literal('2')}), text({literal('-X1:2')}), "
        f"text({literal('-X2:2')}), text({literal('')})"
    )
    assert row1 in text
    assert row2 in text


def test_cable_table_dropping_a_core_loses_its_own_row():
    """Can-fail: dropping `core2` from `cable.cores` before calling `_cable_table` makes this
    assertion fail -- core 2's full row (`"2"`, `"-X1:2"`, `"-X2:2"`, `""`) would be gone.
    """
    core1 = _core(index=1, end_a_designation="-X1:1", end_b_designation="-X2:1", label="L1")
    core2 = _core(index=2, end_a_designation="-X1:2", end_b_designation="-X2:2", label=None)
    text = _cable_table(_cable(cores=(core1, core2)))
    row2 = (
        f"text({literal('2')}), text({literal('-X1:2')}), "
        f"text({literal('-X2:2')}), text({literal('')})"
    )
    assert row2 in text


# -- end-to-end through `fransys_pdf.source` (CT2, CT4, Y3) -------------------------------


def _harness_document(*, length_mm: int | None):
    """A `HARNESS_DRAWING` document over one zero-core cable, isolated to its own page kind."""
    harness = item("wh1", description="Demo harness")
    cable_part = part("cab1", description="Invented cable")
    cable_product = cable_product_facet("cab1", subject=cable_part.id, core_count=0)
    cable = item("w1", description="Cable one", part=cable_part.id, parent=harness.id)
    cf = cable_facet("w1", subject=cable.id, length_mm=length_mm)
    doc = document(
        "d1",
        preset=DocumentPreset.HARNESS_DRAWING,
        subject=harness,
        cover="# Cover",
        notes=None,
        remove=(K.COVER, K.CONTENTS, K.BOM),
    )
    m = model(harness, cable_part, cable_product, cable, cf, doc)
    return m, doc


def test_a_zero_core_cable_builds_with_no_data_row():
    """CT4 end-to-end: no `Conductor` carries this cable, so the drawing's own table (reached
    through `source`, not `_cable_page` directly) prints the header only.
    """
    m, doc = _harness_document(length_mm=1500)
    text = source(m, doc.id, {})
    record = documents(m)[doc.id]
    (found,) = harness_cables_for(m, record, (K.HARNESS_DRAWING,))
    assert found.cores == ()
    assert _cable_table(found) in text


def _heading_of(length_mm: int | None) -> str:
    """The cable heading text `source` writes for one cable with `length_mm`."""
    m, doc = _harness_document(length_mm=length_mm)
    text = source(m, doc.id, {})
    return text.split("#strong(text(")[1].split("))")[0]


def test_a_cable_heading_is_its_designation_and_length_when_it_has_one():
    """Designer ruling (pdf-0021): `-W1, 1500 mm` with a length."""
    assert _heading_of(1500) == literal("-WH1, 1500 mm")


def test_a_cable_heading_is_its_designation_alone_without_a_length():
    """No `length_mm`: the designation and nothing after it."""
    assert _heading_of(None) == literal("-WH1")


def _system_document_with_one_external_end():
    """A SYSTEM document over one top-level cable with one real, external end (`X3`)."""
    cable_part = part("cab1", description="Invented 1-core cable")
    cable = item("w1", description="Cable one", part=cable_part.id)
    cf = cable_facet("w1", subject=cable.id, length_mm=1500)
    cpf = cable_product_facet("w1", subject=cable_part.id, core_count=1)
    m1_item, m1_fn, m1_port = pin("m1", "M1")
    x3_item, x3_fn, x3_port = pin("x3", "X3")
    x3_item = replace(x3_item, external=True)
    core = conductor(
        "core-1", a=m1_port.id, b=x3_port.id, kind=ConductorKind.CORE, carrier=cable.id
    )
    core_marker = core_facet("core-1", subject=core.id, index=1)
    doc = document(
        "d1",
        preset=DocumentPreset.SYSTEM,
        cover="# Cover",
        notes=None,
        remove=(K.COVER, K.CABLE_LIST, K.BOM),
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
    return m, doc


def test_source_prints_the_by_others_note_on_its_own_line_after_the_heading():
    """Y3: the note is its own heading line, not a continuation of the bold designation/mpn/
    description/length line -- it must read as `...length by others: ...`, not `...15000 mm
    by others: ...` on one line. Can-fail: joining the heading and the note with a plain `\\n`
    (no `#linebreak()`) reads as inline in Typst, since a bare source newline is a soft break in
    markup mode; that patch makes this assertion fail (see `docs/decisions/pdf-0018-...md`).
    """
    m, doc = _system_document_with_one_external_end()
    text = source(m, doc.id, {})
    record = documents(m)[doc.id]
    (found,) = harness_cables_for(m, record, (K.HARNESS_DRAWING,))
    heading = _cable_heading(found)
    note = "by others: -X3"
    assert f"#strong(text({literal(heading)}))\n#linebreak()#text({literal(note)})" in text
