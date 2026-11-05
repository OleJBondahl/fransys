"""Decision model-0077, through the facade: two pins that print one text stop the build.

The throwaway demo part `DEMO-DUAL` (a copy of `demo_parts` plus one part file, in `tmp_path`;
`examples/demo-parts` is untouched) has two non-connector functions `ch1` and `ch2`, with one pin
"""

import dataclasses
import shutil
from pathlib import Path
from typing import Any

import fransys as fr
import fransys_parts
import pytest
from _expected_codes import expect_codes
from _model_build_cover import cabinet_document
from fransys_author.design import Design

from fransys_model.kernel import Draft, Severity
from fransys_model.layout import LinkMarker, layout_of
from fransys_model.vocab import PortTemplate

_PROJECT: dict[str, Any] = {
    "title": "Duplicate pins",
    "number": "P-1077",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}
_CODE = "PORT_DESIGNATION_DUPLICATE"
_MPN = "DEMO-DUAL"
_PART = f"""schema = 2

[part]
mpn = "{_MPN}"
manufacturer = "Demo"
description = "Device with two channels"
category = "generic"
class_code = "U"

[[function]]
name = "ch1"
kind = "load"
ports = [{{ name = "7", role = "generic" }}]

[[function]]
name = "ch2"
kind = "load"
ports = [{{ name = "8", role = "generic" }}]
"""


def _collide(parts: Draft) -> Draft:
    """`parts` with the port template `8` renamed `7`, which the library lint refuses."""
    collided = Draft()
    for original in parts.records():
        record = original
        if isinstance(record, PortTemplate) and record.name == "8":
            record = dataclasses.replace(record, name="7")
        origin = parts.origin_of(record.id)
        assert origin is not None
        collided.add(record, origin=origin)
    return collided


def _build(root: Path, *, collide: bool) -> fr.BuildResult:
    """Build the two-plug design over a copy of `demo_parts` plus `DEMO-DUAL`."""
    import demo_parts

    library = root / "demo_parts"
    shutil.copytree(Path(demo_parts.__file__).parent, library, ignore=shutil.ignore_patterns("__*"))
    (library / "parts" / "dual.toml").write_text(_PART, encoding="utf-8")
    parts = fransys_parts.load_path(library)
    if collide:
        parts = _collide(parts)
    second = "7" if collide else "8"
    d = Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-25", text="First issue", created="XX")
    cabinet, field = d.location("A", "Cabinet"), d.location("B", "Field")
    group = d.group("G", "Pump")
    a1 = d.item(_MPN, tag="A1", at=field, group=group)
    p1 = d.item("DEMO-CONN-2P", tag="P1", at=cabinet, group=group)
    p2 = d.item("DEMO-CONN-2P", tag="P2", at=cabinet, group=group)
    cable = d.cable("DEMO-CBL-4G1.5", tag="W1")
    cable.core(1, p1["1"], a1.fn("ch1")["7"])
    cable.core(2, p2["1"], a1.fn("ch2")[second])
    return fr.build(parts, d.draft(), cabinet_document(cabinet), cabinet_document(field))


def test_the_build_returns_one_error_naming_the_item_the_functions_and_the_text(
    tmp_path: Path,
) -> None:
    """(a) No `LayoutError`: one `PORT_DESIGNATION_DUPLICATE` `ERROR` says `A1`, `ch1`, `ch2`."""
    # UNDO: fransys_model/derive/passes/numbering.py: `number`'s `findings.extend(
    #   _port_duplicates(...))` call removed (the build raises `LayoutError` in `_build`)
    duplicate = _build(tmp_path, collide=True)
    expect_codes(duplicate, _CODE)
    (finding,) = [f for f in duplicate.findings if f.code == _CODE]
    assert finding.severity is Severity.ERROR
    for part in ("A1", "ch1", "ch2", repr("-A1:7"), "pin markings"):
        assert part in finding.message
    assert "⟨" not in finding.message
    assert [f.severity for f in duplicate.findings].count(Severity.ERROR) == 1


def test_the_build_stops_before_layout_and_check_reports_the_error(tmp_path: Path) -> None:
    """(b) G1: the model has no layout; `check` has the ERROR."""
    # UNDO: fransys_model/derive/passes/numbering.py: `_port_duplicates` `severity=
    #   Severity.ERROR` -> `Severity.WARNING` (layout runs and raises `LayoutError` in `_build`)
    duplicate = _build(tmp_path, collide=True)
    assert layout_of(duplicate.model, LinkMarker) == {}
    findings = fr.check(duplicate)
    assert len([f for f in findings if f.severity is Severity.ERROR]) == 1
    expect_codes(duplicate, _CODE)


def test_write_raises_build_errors_and_writes_nothing(tmp_path: Path) -> None:
    """(b2) `write` raises `BuildFailedError` for the ERROR and leaves `out_dir` empty.

    Without the guard, wireviz refuses the two equal `-A1:7` ends with a bare `Exception`
    ("Pins are not unique") before the F5 gate is reached.
    """
    # UNDO: fransys/pipeline.py: `_result_svgs`'s `return _svgs(drawn) if laid_out else {}`
    #   -> `return _svgs(drawn)` (the bare wireviz `Exception`)
    duplicate = _build(tmp_path / "build", collide=True)
    out_dir = tmp_path / "out"
    with pytest.raises(fr.BuildFailedError) as raised:
        fr.write(duplicate, out_dir=out_dir)
    assert len(raised.value.findings) == 1
    expect_codes(duplicate, _CODE)
    assert list(out_dir.iterdir()) == []


def test_the_same_wiring_with_the_pins_named_apart_builds_clean_and_is_laid_out(
    tmp_path: Path,
) -> None:
    """(c) Pins `7` and `8` print `-A1:7` and `-A1:8`: no ERROR, and layout ran."""
    # UNDO: fransys_model/derive/passes/numbering.py: `_port_duplicates` group key
    #   `port_designation(model, port)` -> `"pin"` (every port of `A1` collides: the ERROR is back)
    apart = _build(tmp_path, collide=False)
    assert Severity.ERROR not in {f.severity for f in apart.findings}
    assert _CODE not in {f.code for f in apart.findings}
    # The two-core line -W1 leaves each of its two sets in one stub
    stubs = layout_of(apart.model, LinkMarker).values()
    assert len(stubs) == 2
    assert all("line_stub" in m.key for m in stubs)
