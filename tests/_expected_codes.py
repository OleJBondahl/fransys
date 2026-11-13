"""The one door for a test that asserts the finding codes its build must show (designer R1176, CC8.3).

`expect_codes(result, "CONNECTION_NOT_DRAWN")` fails unless the build shows each code, and tells the rel-sweep that the
build's correctness code is asserted here, so `finding_rise` anchors it without a KNOWN-ISSUES row.
"""

import importlib
import os

DECLARED: set[str] = set()  # codes a field-case module asserted through expect_codes; tests/field_cases/conftest.py gates the other ERRORs
REFUSED: list[object] = []  # builds that showed MATES_DISABLED or SCREEN_DISABLED; conftest fails the test unless it asserts the refusal


def expect_codes(result, *codes: str) -> None:
    """Assert that `result` (a `fr.build` result) shows every code in `codes`; the sweep reads the call."""
    DECLARED.update(codes)
    shown = sorted({f.code for f in result.findings})
    missing = sorted(set(codes) - set(shown))
    if {"MATES_DISABLED", "SCREEN_DISABLED"} & set(codes):
        REFUSED.clear()
    assert not missing, f"the build does not show {missing}; it shows {shown}"
    if "REL_SWEEP_RECORD" in os.environ:
        # by name: the sweep module is the maintainers' (internal/scripts), absent from the export, so ty resolves nothing here
        importlib.import_module("rel_sweep").expect(result, codes)
