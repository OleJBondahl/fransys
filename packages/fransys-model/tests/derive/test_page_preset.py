"""`derive.page_preset`: each page kind has one preset, equal to the sites inventory."""

import pytest

from fransys_model.derive import ListKey, PageForm, PagePreset, page_preset
from fransys_model.kernel import ModelError
from fransys_model.vocab import PageKind
from fransys_model.vocab import page_forms as forms

_F = PageForm
_L = ListKey

# kind -> (form, list key, self_framed): the .fransys/PAGE-PRESETS-SITES.md inventory, row for row
EXPECTED = {
    PageKind.COVER: (_F.COVER, None, False),
    PageKind.NOTES: (_F.NOTES, None, False),
    PageKind.SHEET_INDEX: (_F.SHEET_INDEX, None, False),
    PageKind.CONTENTS: (_F.CONTENTS, None, False),
    PageKind.BLOCK_DIAGRAM: (_F.BLOCK_DIAGRAM, None, True),
    PageKind.SCHEMATIC: (_F.SCHEMATIC, None, True),
    PageKind.HARNESS_DRAWING: (_F.HARNESS_DRAWING, None, True),
    PageKind.PLC_LIST: (_F.LIST, _L.PLC, False),
    PageKind.TERMINAL_LIST: (_F.LIST, _L.TERMINAL, False),
    PageKind.CONNECTOR_LIST: (_F.LIST, _L.CONNECTOR, False),
    PageKind.WIRE_LABEL_LIST: (_F.LIST, _L.WIRE_LABEL, False),
    PageKind.DESIGNATION_LIST: (_F.LIST, _L.DESIGNATION, False),
    PageKind.CABLE_LIST: (_F.CABLE_LIST, _L.CABLE, False),
    PageKind.BOM: (_F.LIST, _L.BOM, False),
}


def test_every_kind_has_exactly_one_preset() -> None:
    assert set(EXPECTED) == set(PageKind)
    assert set(forms.PAGE_FORMS) == set(PageKind)


@pytest.mark.parametrize("kind", list(PageKind))
def test_preset_equals_the_inventory(kind: PageKind) -> None:
    preset = page_preset(kind)
    assert (preset.form, preset.list_key, preset.self_framed) == EXPECTED[kind]
    assert preset.kind is kind


def test_list_key_is_set_exactly_for_the_list_kinds() -> None:
    with_key = {kind for kind in PageKind if page_preset(kind).list_key is not None}
    assert with_key == {
        kind for kind in PageKind if kind.name.endswith("LIST") or kind.name == "BOM"
    }
    assert len({page_preset(kind).list_key for kind in with_key}) == len(with_key)


def test_page_preset_is_pure() -> None:
    assert page_preset(PageKind.BOM) == page_preset(PageKind.BOM)
    assert isinstance(page_preset(PageKind.COVER), PagePreset)


def test_a_kind_with_no_preset_raises_naming_it(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delitem(forms.PAGE_FORMS, PageKind.BOM)
    with pytest.raises(ModelError, match="BOM"):
        page_preset(PageKind.BOM)
