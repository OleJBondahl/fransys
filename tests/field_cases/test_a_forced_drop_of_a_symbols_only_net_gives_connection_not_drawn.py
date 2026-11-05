"""Field case: a net a set cannot carry on with a stub is a conductor not drawn, never silent (R828, R1611).
The drop is forced, so the file's one build carries CONNECTION_NOT_DRAWN by its input (R1708); it was in test_core_path_lays_out_a_unit_document."""

from typing import TYPE_CHECKING, Any

from _expected_codes import expect_codes
from fransys_el import placement_sets
from test_core_path_lays_out_a_unit_document import build_room
lazy import pytest

if TYPE_CHECKING:
    from pathlib import Path


def test_a_forced_drop_of_a_symbols_only_net_gives_connection_not_drawn(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """R828, R1611: a net a set cannot carry on with a stub is a conductor not drawn: CONNECTION_NOT_DRAWN, never silent."""
    assert "CONNECTION_NOT_DRAWN" not in {f.code for f in build_room(tmp_path, beyond=True).findings}
    real = placement_sets._net

    def drop(net: Any, symbols: Any, *rest: Any) -> Any:
        made = real(net, symbols, *rest)
        return None if made is not None and made.cut and any(s.startswith("H1") for s in symbols) else made

    monkeypatch.setattr(placement_sets, "_net", drop)
    expect_codes(build_room(tmp_path, beyond=True), "CONNECTION_NOT_DRAWN")
