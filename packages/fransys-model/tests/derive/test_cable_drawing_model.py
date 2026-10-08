"""The cable drawing's subject, block key, block cables and texts (CT5, CD3, CD7, CD9, CD10)."""

import dataclasses
from decimal import Decimal

from cable_drawing_builders import cable, device, edit
from plant import Plant
from query_builders import make_core, make_node, make_part, make_placement

from fransys_model import derive
from fransys_model.derive import cable_drawing
from fransys_model.derive.cable_drawing import (
    block_cables,
    cable_block_key,
    cable_heading,
    cable_subject,
    core_text,
    end_by_others,
    end_label,
)
from fransys_model.derive.drawing_text import external_note
from fransys_model.kernel import Id, make_id
from fransys_model.kernel.ids import render_id
from fransys_model.vocab.facets.wire import WireFacet
lazy from fransys_model.vocab.connectivity import Conductor
lazy from fransys_model.vocab.core import Item, Unit


def _two_cable_harness() -> tuple[Plant, dict[str, Id[Item]]]:
    """A loose cable, a lone cable, a two-cable harness and a harness with a part."""
    plant = Plant()
    loose = cable(plant, "loose", "W0")
    lone_harness = plant.item("h-lone", designation="WH1")
    lone = cable(plant, "lone", "W1", parent=lone_harness)
    pair = plant.item("h-pair", designation="WH2")
    second = cable(plant, "second", "W3", parent=pair)
    first = cable(plant, "first", "W2", parent=pair)
    nameless = cable(plant, "nameless", None, parent=pair)
    owned = plant.item("h-owned", designation="WH3", part=make_part(plant, "hp", "MPN-H"))
    solo = cable(plant, "solo", "W4", parent=owned)
    ids = {
        "loose": loose, "lone": lone, "pair": pair, "second": second, "first": first,
        "nameless": nameless, "owned": owned, "solo": solo,
    }  # fmt: skip
    return plant, ids


def test_cable_subject_is_the_cable_unless_its_harness_has_two_cables_or_a_part() -> None:
    """A loose or lone cable is its own subject; the harness of two cables or of a part is one."""
    plant, ids = _two_cable_harness()
    model = plant.model()
    assert cable_subject(model, ids["loose"]) == ids["loose"]
    assert cable_subject(model, ids["lone"]) == ids["lone"]
    assert cable_subject(model, ids["first"]) == ids["pair"]
    assert cable_subject(model, ids["solo"]) == ids["owned"]


def test_cable_block_key_is_the_rendered_subject_or_unit_tilde_subject() -> None:
    """Absolute: `render_id(subject)`; in a unit `<unit>~<subject>`; six inputs, six keys."""
    plant, ids = _two_cable_harness()
    u1, u2 = plant.unit("u1"), plant.unit("u2")
    assert cable_block_key(None, ids["loose"]) == render_id(ids["loose"])
    assert cable_block_key(u1, ids["loose"]) == f"{render_id(u1)}~{render_id(ids['loose'])}"
    keys = {
        cable_block_key(unit, subject)
        for unit in (None, u1, u2)
        for subject in (ids["loose"], ids["pair"])
    }
    assert len(keys) == 6


def test_block_cables_of_a_harness_are_its_readable_cables_in_designation_order() -> None:
    """`W2` before `W3`; the cable with no designation is left out; a cable subject is itself."""
    plant, ids = _two_cable_harness()
    model = plant.model()
    assert [c.cable for c in block_cables(model, ids["pair"], None)] == [
        ids["first"],
        ids["second"],
    ]
    assert [c.cable for c in block_cables(model, ids["loose"], None)] == [ids["loose"]]
    assert block_cables(model, ids["nameless"], None) == ()


def _one_cable() -> tuple[Plant, Id[Item], Id[Conductor]]:
    """Cable `W3` (no parent) with one core `1` between two invented devices."""
    plant = Plant()
    w3 = cable(plant, "w3", "W3", shielded=True, length=3000)
    _, a = device(plant, "a", "A1", "1")
    _, b = device(plant, "b", "B1", "1")
    core = make_core(plant, "c1", w3, (a["1"], b["1"]), index=1)
    return plant, w3, core


def test_core_text_is_index_colour_label_with_single_spaces() -> None:
    """`1 BK1 no. 1`, `4 GNYE`, `5` (colour "" and no label), and `4` with a label but no colour."""
    plant, w3, _ = _one_cable()
    (row,) = block_cables(plant.model(), w3, None)
    (core,) = row.cores

    def text(index: int, colour: str, label: str | None) -> str:
        return core_text(dataclasses.replace(core, index=index, colour=colour, label=label))

    assert text(1, "BK1", "no. 1") == "1 BK1 no. 1"
    assert text(4, "GNYE", None) == "4 GNYE"
    assert text(5, "", None) == "5"
    assert text(4, "", "no. 4") == "4 no. 4"


def test_cable_heading_is_designation_then_shielded_then_length() -> None:
    """`-W3, shielded, 3000 mm`; each of the two words only when the cable has the fact."""
    plant, w3, _ = _one_cable()
    (row,) = block_cables(plant.model(), w3, None)
    assert cable_heading(plant.model(), row, None) == "-W3, shielded, 3000 mm"
    plain = dataclasses.replace(row, shielded=False, length_mm=None)
    assert cable_heading(plant.model(), plain, None) == "-W3"
    assert (
        cable_heading(plant.model(), dataclasses.replace(row, shielded=False), None)
        == "-W3, 3000 mm"
    )


def test_cable_heading_ends_by_others_for_an_external_cable_in_the_absolute_reading() -> None:
    """An external cable, or one in an external harness, says `by others`; a unit's reading not."""
    plant, ids = _two_cable_harness()
    unit = plant.unit("u1")
    edit(plant, ids["loose"], external=True)
    edit(plant, ids["pair"], external=True)
    model = plant.model()
    (loose,) = block_cables(model, ids["loose"], None)
    (in_harness, _) = block_cables(model, ids["pair"], None)
    assert cable_heading(model, loose, None) == f"-W0, {external_note()}"
    assert cable_heading(model, in_harness, None) == f"-WH2-W2, {external_note()}"
    assert cable_heading(model, loose, unit) == "-W0"


def _external_end() -> tuple[Plant, Id[Item], Id[Item], tuple[Id[Unit], Id[Unit]]]:
    """External `M1` at `+EXT` and plain `N1`, both in no unit, and a unit `u` nested in `top`."""
    plant = Plant()
    ext = make_node("ext", None)
    plant.add(ext)
    m1, _ = device(plant, "m1", "M1", "1", external=True)
    n1, _ = device(plant, "n1", "N1", "1")
    plant.add(make_placement("m1-loc", m1, ext.id))
    top = plant.unit("top")
    nested = plant.unit("nested", parent=top)
    return plant, m1, n1, (top, nested)


def test_end_by_others_and_label_mark_an_external_end_only_in_the_absolute_reading() -> None:
    """`+EXT-M1 (by others)` absolute; plain `+EXT-M1` in a top-level unit; `N1` never marked."""
    plant, m1, n1, (top, _) = _external_end()
    model = plant.model()
    assert end_by_others(model, m1, None) is True
    assert end_label(model, m1, None) == "+EXT-M1 (by others)"
    assert end_by_others(model, m1, top) is False
    assert end_label(model, m1, top) == "+EXT-M1"
    assert end_by_others(model, n1, None) is False
    assert end_label(model, n1, None) == "-N1"


def test_a_blank_end_in_a_nested_units_reading_has_an_empty_label_and_no_mark() -> None:
    """`M1` is outside the nested unit (CD11): label `""`, never marked."""
    plant, m1, _, (_, nested) = _external_end()
    model = plant.model()
    assert end_label(model, m1, nested) == ""
    assert end_by_others(model, m1, nested) is False


def test_the_surface_is_exactly_the_sixteen_names_and_none_reaches_derive() -> None:
    """The module's `__all__`; `all_cables` and `all_unit_cables` stay off every `__all__`."""
    names = {
        "DrawnPin", "DrawnWire", "block_cables", "block_drawn", "block_wires", "cable_block_key",
        "cable_heading", "cable_subject",
        "core_text", "drawn_blocks", "drawn_pins", "end_by_others", "end_label", "end_rows",
        "row_links",
        "wire_harness_subjects",
    }  # fmt: skip
    assert sorted(cable_drawing.__all__) == sorted(names)
    assert not names & set(derive.__all__)
    assert not {"all_cables", "all_unit_cables"} & (
        set(cable_drawing.__all__) | set(derive.__all__)
    )


def test_a_core_label_comes_from_its_wire_facet() -> None:
    """`core_text` of a real core carries the wire facet's label after index and colour."""
    plant, w3, conductor = _one_cable()
    plant.add(
        WireFacet(
            id=make_id(WireFacet, ("c1", "wire")),
            key=("c1", "wire"),
            subject=conductor,
            colour="black",
            gauge_mm2=Decimal("0.5"),
            length_mm=None,
            label="no. 1",
        )
    )
    (row,) = block_cables(plant.model(), w3, None)
    assert core_text(row.cores[0]) == "1 colour-1 no. 1"
