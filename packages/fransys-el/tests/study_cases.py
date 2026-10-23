"""The five cross-link instances of the study (nontree.md), rebuilt from the builders it names.

Each row loads the case builder of the field-case test the study names (by path, as the tests
cannot import a `test_` module) and returns its model. Where the test builds inline in its body
or a fixture, the same few lines are repeated here around the module's own unit.
"""

import importlib.util
import tempfile
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING

import fransys as fr

if TYPE_CHECKING:
    from types import ModuleType

    from fransys_model.kernel import Model

__all__ = ["ROWS", "study_model"]

CASES = Path(__file__).resolve().parents[3] / "tests" / "field_cases"
ROWS = {
    "seal": "test_a_marker_rail_keeps_off_another_nets_wire",
    "pilot": "test_net_contact_is_not_a_spare",
    "channels": "test_a_bank_of_coils_returned_to_channels_does_not_cross",
    "units": "test_a_unit_profile_keeps_cross_references_to_the_cabinet_pages",
    "drawn": "test_a_contact_image_lives_at_its_functions_home",
}


@cache
def field_case(name: str) -> ModuleType:
    """The field-case module `name`, loaded once from its file."""
    spec = importlib.util.spec_from_file_location(name, CASES / f"{name}.py")
    if spec is None or spec.loader is None:
        msg = f"cannot load {name}"
        raise ImportError(msg)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _document(folder: str, target: str) -> fr.Draft:
    cover = Path(folder) / "own.md"
    cover.write_text("# Study\n", encoding="utf-8")
    return fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, target, cover=cover)


def _seal(case: ModuleType) -> Model:
    d = fr.design("demo_parts")
    d.add(case._starter, "U1")
    return fr.build(d).model


def _units(case: ModuleType) -> Model:
    with tempfile.TemporaryDirectory() as folder:
        # The study's instance w02 is the second build of its test: the unit body's profile.
        return case._build(Path(folder), design=None, in_body=case._UNIT_GAP).model


def _drawn(case: ModuleType) -> Model:
    d = fr.design("demo_parts")
    d.add(case._cab, "U1")
    with tempfile.TemporaryDirectory() as folder:
        return fr.build(d, _document(folder, "demo-cab")).model


def study_model(row: str) -> Model:
    """The model of study row `row` (a key of `ROWS`), built by its named test's builder."""
    case = field_case(ROWS[row])
    builders = {
        "seal": _seal,
        "pilot": lambda c: c._built_net_contact(),
        "channels": lambda c: c._built(),
        "units": _units,
        "drawn": _drawn,
    }
    return builders[row](case)
