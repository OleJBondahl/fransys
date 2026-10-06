"""`scripts/cov_floors.py`: the pure coverage-floor core (measurement, check).

Loaded by file path (`importlib.util.spec_from_file_
location`), since the script is not a package module. Every case builds a small in-memory
`coverage.json`-shaped dict and a `Decimal` floors dict by hand; there is no real `pytest --cov`
run anywhere in this file.
"""

from __future__ import annotations

import importlib.util
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "fransys_cov_floors", ROOT / "scripts" / "cov_floors.py"
)
if _spec is None or _spec.loader is None:
    msg = "could not load scripts/cov_floors.py"
    raise ImportError(msg)
cov_floors = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = cov_floors
_spec.loader.exec_module(cov_floors)


def _report(files: dict[str, tuple[int, int]]) -> dict:
    """A `coverage.json`-shaped dict from `{path: (num_statements, missing_lines)}`."""
    return {
        "files": {
            path: {"summary": {"num_statements": statements, "missing_lines": missing}}
            for path, (statements, missing) in files.items()
        }
    }


# --- check: below floor, missing from floors, the vacuous-pass guard -----------------------


def test_a_package_below_its_floor_fails_naming_the_package_measured_and_floor():
    expected = {"fransys_model": "packages/fransys-model"}
    floors = {"fransys_model": Decimal("99.0")}
    report = _report({"packages/fransys-model/src/fransys_model/x.py": (100, 5)})
    measured = cov_floors.measure_packages(report, expected)
    failures = cov_floors.check(expected, floors, measured)
    assert failures == ("FAIL fransys_model: 95.0 measured, floor 99.0 (coverage-floors.toml)",)


def test_a_package_missing_from_the_floors_dict_fails_naming_it():
    expected = {"fransys_model": "packages/fransys-model"}
    floors: dict[str, Decimal] = {}
    report = _report({"packages/fransys-model/src/fransys_model/x.py": (10, 0)})
    measured = cov_floors.measure_packages(report, expected)
    failures = cov_floors.check(expected, floors, measured)
    assert failures == ("FAIL fransys_model: missing from coverage-floors.toml",)


def test_the_vacuous_pass_guard_fails_a_package_with_zero_matching_files():
    # The report has files, but none of them are under this package's src/ -- the grouping must
    # fail loudly, never silently report zero failures.
    expected = {"fransys_model": "packages/fransys-model"}
    floors = {"fransys_model": Decimal("90.0")}
    report = _report({"packages/fransys/src/fransys/unrelated.py": (10, 0)})
    measured = cov_floors.measure_packages(report, expected)
    failures = cov_floors.check(expected, floors, measured)
    assert failures == ("FAIL fransys_model: no measured coverage found (coverage.json)",)


# --- grouping: by path segment, never by a name prefix --------------------------------------


def test_files_are_grouped_by_path_segment_never_by_a_name_prefix():
    # "fransys" is a literal string-prefix of "fransys_model": a name-prefix grouping bug
    # would fold fransys-model's file into fransys's total too.
    expected = {
        "fransys": "packages/fransys",
        "fransys_model": "packages/fransys-model",
    }
    report = _report(
        {
            "packages/fransys/src/fransys/x.py": (4, 0),  # 100%
            "packages/fransys-model/src/fransys_model/y.py": (8, 4),  # 50%
        }
    )
    measured = cov_floors.measure_packages(report, expected)
    assert measured["fransys"] == Decimal(100)
    assert measured["fransys_model"] == Decimal(50)


def test_files_are_grouped_the_same_way_with_windows_backslash_keys():
    # coverage.py's real JSON report on this machine keys files with backslashes; the same
    # grouping must hold after normalizing the separator.
    expected = {
        "fransys": "packages/fransys",
        "fransys_model": "packages/fransys-model",
    }
    report = _report(
        {
            "packages\\fransys\\src\\fransys\\x.py": (4, 0),
            "packages\\fransys-model\\src\\fransys_model\\y.py": (8, 4),
        }
    )
    measured = cov_floors.measure_packages(report, expected)
    assert measured["fransys"] == Decimal(100)
    assert measured["fransys_model"] == Decimal(50)
