"""The census (tests/surface_census.py) and the ratchet stock helpers, with their can-fail cases."""

import sys
import textwrap

import gate_scan
import pytest
from surface_census import census, door_census


def _synthetic(tmp_path):
    """A package `synthpkg` and one reader file; returns the scan dirs and the census root."""
    pkg = tmp_path / "packages" / "synthpkg" / "src" / "synthpkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text(
        textwrap.dedent(
            """
            from dataclasses import dataclass

            @dataclass(frozen=True)
            class Row:
                x: int

            @dataclass(frozen=True)
            class Wrapped:
                rows: list["Row"]

            def make() -> Wrapped:
                return Wrapped([Row(1)])

            class Lonely: ...

            __all__ = ["Row", "Wrapped", "make", "Lonely"]
            """
        )
    )
    reader = tmp_path / "scripts"
    reader.mkdir()
    (reader / "use.py").write_text("from synthpkg import make\nmake()\n")
    return [reader], tmp_path


def test_a_name_read_only_through_a_signature_counts_as_read(tmp_path, monkeypatch):
    scan, root = _synthetic(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path / "packages" / "synthpkg" / "src"))
    sys.modules.pop("synthpkg", None)
    rows = census(["synthpkg"], scan=scan, root=root)
    assert rows["synthpkg.make"].outside == ("scripts/use.py",)
    assert rows["synthpkg.Wrapped"].transitive
    assert not rows["synthpkg.Wrapped"].unread
    assert rows["synthpkg.Row"].outside == ()
    assert not rows["synthpkg.Row"].transitive
    assert rows["synthpkg.Row"].unread, "one signature hop only: Row hangs off an unread name"
    assert rows["synthpkg.Lonely"].unread
    sys.modules.pop("synthpkg", None)


def test_the_real_kernel_census_lists_no_more_unread_than_the_old_script():
    """The old script listed 25 unread kernel names (measured at 75584c550); NS-2 adds five, and
    FAN-2 (R338) one: `parent_chain` lost its one outside reader with the old engine: 29.

    Reads the kernel rows of `door_census()`, the build test_ratchet_unread_doors shares.
    """
    rows = {k: r for k, r in door_census().items() if r.module == "fransys_model.kernel"}
    assert 0 < sum(not r.outside for r in rows.values()) <= 29
    assert sum(r.unread for r in rows.values()) <= sum(not r.outside for r in rows.values())
    assert any(r.transitive for r in rows.values()), "no name was read through a signature"


def test_the_stock_helpers_read_and_fail_both_ways(tmp_path, monkeypatch):
    path = tmp_path / "ratchets.toml"
    path.write_text("[demo]\nstock = 3\ntwins = 7\n")
    monkeypatch.setattr(gate_scan, "RATCHETS", path)
    assert gate_scan.stock("demo") == 3
    assert gate_scan.stock("demo", "twins") == 7
    gate_scan.check_stock("demo", 3, 3)
    with pytest.raises(AssertionError, match=r"demo: 4 above its stock 3"):
        gate_scan.check_stock("demo", 4, 3)
    with pytest.raises(AssertionError, match=r"demo: 2 below its stock 3: lower tests/ratchets"):
        gate_scan.check_stock("demo", 2, 3)
