"""Shared fixtures: the layout package's golden laid-out cabinet (spec, "Test data").

Render's tests read the golden JSON files directly, loaded with the model's `loads`;
they never import `fransys_layout` (the boundary gate holds render to
`fransys_model`, `graphical_symbols`, `electrical_symbols`).

The golden's own recorded `library_version` (a snapshot from whenever it was regenerated) is
replaced on load by the currently INSTALLED `electrical_symbols.library_version()` (decision
layout-0046's normalisation, applied here to the installed value rather than a fixed
placeholder): `check.py`'s `LIBRARY_VERSION_MISMATCH` compares a placement's recorded value
against exactly that installed value, so leaving the golden's own stale recording in place
would fire `LIBRARY_VERSION_MISMATCH` on every release that moves electrical-symbols' version,
for a reason that has nothing to do with the layout itself. `produced_by` is untouched: no
render check reads it.
"""

import sys
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest

import fransys_model.layout  # noqa: F401 -- imported to register the layout vocabulary
import fransys_model.vocab  # noqa: F401 -- registers vocab record kinds for `loads`
from electrical_symbols import library_version
from fransys_model.kernel import Model, Origin, evolve, loads

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

    from fransys_model.kernel import Record

# --import-mode=importlib leaves the test directory off sys.path; tests import `_cable_build` by
# name. Workspace rule: conftests append to sys.path, never insert(0).
sys.path.append(str(Path(__file__).parent))

_GOLDEN_DIR = (
    next(
        p
        for p in Path(__file__).resolve().parents
        if (p / "fransys-layout" / "tests" / "golden").is_dir()
    )
    / "fransys-layout"
    / "tests"
    / "golden"
)
_NORMALIZE_ORIGIN = Origin(file=__file__, line=1, note="golden library-version normalisation")


def _with_installed_library_version(model: Model) -> Model:
    """`model` with every `library_version` field set to the installed
    `electrical_symbols.library_version()`.
    """
    installed = library_version()
    remove_ids = []
    put_records = []
    for table in model.tables.values():
        for record_id, record in table.items():
            if getattr(record, "library_version", None) not in (None, installed):
                remove_ids.append(record_id)
                put_records.append(
                    cast(
                        "Record",
                        replace(cast("DataclassInstance", record), library_version=installed),
                    )
                )
    if not put_records:
        return model
    return evolve(model, remove=remove_ids, put=put_records, origin=_NORMALIZE_ORIGIN)


def _load(name: str) -> Model:
    raw = loads((_GOLDEN_DIR / name).read_text(encoding="utf-8"))
    return _with_installed_library_version(raw)


@pytest.fixture(scope="session")
def cabinet_laid_out() -> Model:
    """The wide cabinet: 2 pages, 6 link markers (all star)."""
    return _load("cabinet_laid_out.json")


@pytest.fixture(scope="session")
def cabinet_narrow_laid_out() -> Model:
    """The narrow cabinet: 5 pages, 8 link markers (star and plain)."""
    return _load("cabinet_narrow_laid_out.json")


@pytest.fixture(scope="session")
def cabinet_two_location_laid_out() -> Model:
    """The two-location cabinet: 2 pages, 7 link markers (4 of them off stubs)."""
    return _load("cabinet_two_location_laid_out.json")
