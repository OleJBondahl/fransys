"""R2 (order PERF-DRAFT, decision model-0093): `_strip_key` and `s.unit`'s two error-path
scans use `Draft.record_of`, not `Draft.records()` — ordinary authoring never re-sorts the
whole draft to find one record it already knows the id of."""

import pytest
from fransys_author import AuthorError, Design

from fransys_model.kernel import Draft

_STRIP_COUNT = 20


def test_authoring_many_bridges_and_a_repeated_unit_calls_records_zero_times(parts, monkeypatch):
    """Acceptance 2: at least 20 bridged strips plus a unit built twice (the second call
    hits `s.unit`'s two `record_of` scans) call `Draft.records()` zero times."""
    d = Design(parts)  # build_catalogue's one records() call happens here, outside the span
    calls = 0
    original = Draft.records

    def counting(self: Draft) -> tuple:
        nonlocal calls
        calls += 1
        return original(self)

    monkeypatch.setattr(Draft, "records", counting)

    s = d.scope("u1")
    s.unit("demo-unit", revision=1, interface="1")
    for i in range(_STRIP_COUNT):
        strip = d.strip(f"X{i}")
        t1, t2 = strip.terminal("TEST-TB"), strip.terminal("TEST-TB")
        d.bridge(t1, t2)
    with pytest.raises(AuthorError, match=r"already has a unit \('demo-unit'\)"):
        s.unit("demo-unit", revision=1, interface="1")

    assert calls == 0
