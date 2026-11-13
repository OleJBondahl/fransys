"""Every field-case build asserts no undeclared ERROR (designer R2244): declare its code with `expect_codes`.

`sys.monitoring` reads each `build` return value, so no src function is patched."""

import sys

import pytest
from _expected_codes import DECLARED
from fransys import pipeline

_BUILT = []
sys.monitoring.use_tool_id(3, "field-error-gate")
sys.monitoring.set_local_events(3, pipeline.build.__code__, sys.monitoring.events.PY_RETURN)


def pytest_runtest_setup():
    """Start each field-case test with no build and no declared code, and record builds until its teardown (fixtures included)."""
    _BUILT.clear()
    DECLARED.clear()
    sys.monitoring.register_callback(3, sys.monitoring.events.PY_RETURN, lambda _code, _off, ret: _BUILT.append(ret))


def pytest_runtest_teardown():
    """Stop recording, so no build outside a field-case test is kept."""
    sys.monitoring.register_callback(3, sys.monitoring.events.PY_RETURN, None)


@pytest.hookimpl(wrapper=True)
def pytest_runtest_call():
    """After a passing test, fail on an ERROR in a build it made (or its module fixtures made) whose code no `expect_codes` named."""
    result = yield
    bad = {f.code for r in _BUILT for f in r.findings if f.severity.name == "ERROR"} - DECLARED
    assert not bad, f"a build shows undeclared ERROR {sorted(bad)}: assert it with expect_codes or fix it"
    return result
