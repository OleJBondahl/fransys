"""The guide's section 12 gates with the real toolkit; each has a broken fixture."""

import json
import re
import shutil
import tempfile
from pathlib import Path

import pytest
from graphical_symbols import (
    Arc,
    Circle,
    LibraryError,
    Line,
    Polyline,
    lint,
    load_bundle,
    load_library,
    repeat,
    stale_build,
    write_build,
)

from electrical_symbols import LIBRARY

ROOT = Path(__file__).parent.parent
# The toolkit names the bundle's package after the standard, `iec60617`, and has no setting to
# change that (T1, D39); scripts/build.py moves the bundle into the package. Delete the
# exceptions this causes when the toolkit gains a package setting.
TOOLKIT_BUNDLE = "src/iec60617/bundle.json"
PACKAGE_BUNDLE = "src/electrical_symbols/bundle.json"
SOURCE = load_library(ROOT)  # a broken file is a loud collection error
SYMBOLS = list(SOURCE)
THROUGH = [s for s in SYMBOLS if any(path.through for path in s.paths)]


def ids(symbols):
    return [s.reference.number for s in symbols]


# The bundle adds one node per port that no node names and sorts the slots by id; every other
# field is equal.
SAME_IN_BUNDLE = (
    "name",
    "kind",
    "status",
    "reference",
    "elements",
    "ports",
    "paths",
    "anchors",
    "pole_pitch",
    "lint_allow",
)


def same(source, bundle):
    return (
        all(getattr(source, field) == getattr(bundle, field) for field in SAME_IN_BUNDLE)
        and tuple(sorted(source.slots, key=lambda slot: slot.id)) == bundle.slots
        and set(source.nodes) <= set(bundle.nodes)
    )


def bundle_problems(bundle, source):
    """What differs between a bundle and the source library, as messages; empty is the gate."""
    found = []
    if numbers(bundle) != numbers(source):
        found.append("the numbers differ")
    for symbol in source:
        number = symbol.reference.number
        if number in bundle.symbols and not same(symbol, bundle.get(number)):
            found.append(f"{number} differs")
    return found


def numbers(library):
    return sorted(s.reference.number for s in library)


def rules(findings):
    return {f.rule for f in findings}


def copy_repo(tmp_path, *stems):
    """Copy library.toml and the named symbol files (with the parts they use) into tmp_path."""
    shutil.copy(ROOT / "library.toml", tmp_path)
    (tmp_path / "symbols").mkdir()
    for stem in stems:
        shutil.copy(ROOT / "symbols" / f"{stem}.toml", tmp_path / "symbols")
    return tmp_path


def edit(root, stem, old, new):
    path = root / "symbols" / f"{stem}.toml"
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def problems(root):
    """The findings load_library raises for a repo, as (rule, message) pairs."""
    with pytest.raises(LibraryError) as raised:
        load_library(root)
    return [(f.rule, f.message) for f in raised.value.findings]


# Gate 1: every file validates and resolves.


def test_every_file_loads_and_resolves():
    files = sorted(p.stem for p in (ROOT / "symbols").glob("*.toml"))
    assert numbers(SOURCE) == files


def test_gate_1_fails_on_a_file_that_does_not_parse(tmp_path):
    root = copy_repo(tmp_path, "make-contact")
    edit(root, "make-contact", 'name = "Make contact, general symbol"', "name = ")
    assert "schema" in {rule for rule, _ in problems(root)}


def test_gate_1_fails_on_a_part_that_does_not_resolve(tmp_path):
    root = copy_repo(tmp_path, "push-button", "make-contact")  # push-button needs actuator-push too
    assert "part-unknown" in {rule for rule, _ in problems(root)}


# Gate 2: zero findings, warnings included, in all 8 orientations.
# `lint` runs every geometric rule in all 8 orientations itself (guide section 9, toolkit README),
# so one call per symbol is the gate.


@pytest.mark.parametrize("symbol", SYMBOLS, ids=ids(SYMBOLS))
def test_symbol_lints_clean(symbol):
    assert lint(symbol) == ()


def test_gate_2_fails_on_a_port_off_the_wiring_grid(tmp_path):
    root = copy_repo(tmp_path, "make-contact")
    edit(
        root,
        "make-contact",
        '{ id = "in",  at = [0, -2], dir = "N" }',
        '{ id = "in", at = [0, -1.5], dir = "N" }',
    )
    assert "port-off-wiring-grid" in rules(lint(load_library(root).get("make-contact")))


# Gate 3: every symbol with a through path also lints clean as repeat(symbol, 3).


def test_some_symbols_have_a_through_path():
    assert THROUGH


@pytest.mark.parametrize("symbol", THROUGH, ids=ids(THROUGH))
def test_repeated_symbol_lints_clean(symbol):
    assert lint(repeat(symbol, 3)) == ()


def test_gate_3_fails_on_the_push_button_without_pole_pitch(tmp_path):
    # The guide's own push-button example, without the `pole_pitch = 8` line (C1, D3).
    root = copy_repo(tmp_path, "push-button", "make-contact", "actuator-push")
    edit(root, "push-button", "pole_pitch = 8\n", "")
    button = load_library(root).get("push-button")
    assert "pitch-overflow" in rules(lint(repeat(button, 3)))


# Gate 4: stale_build reports nothing, except that the bundle lives in the package (T1, D39).


def stale_files(library, root):
    """The stale paths under root, relative and sorted.

    The toolkit expects the bundle at TOOLKIT_BUNDLE, so `stale_build` reports it missing once the
    build script has moved it. That one path is exempt while it is missing, and stale if it exists.
    The bundle at PACKAGE_BUNDLE must hold exactly the bytes the toolkit writes for the bundle.
    """
    stale = {p.relative_to(root).as_posix() for p in stale_build(library, root)}
    if (root / TOOLKIT_BUNDLE).exists():
        stale.add(TOOLKIT_BUNDLE)
    else:
        stale.discard(TOOLKIT_BUNDLE)
    with tempfile.TemporaryDirectory() as scratch:
        write_build(library, Path(scratch))
        wanted = (Path(scratch) / TOOLKIT_BUNDLE).read_bytes()
    packaged = root / PACKAGE_BUNDLE
    if not packaged.is_file() or packaged.read_bytes() != wanted:
        stale.add(PACKAGE_BUNDLE)
    return sorted(stale)


def built_like_the_script(root):
    """Write the build under root and move the bundle into the package, as scripts/build.py does."""
    write_build(SOURCE, root)
    (root / PACKAGE_BUNDLE).parent.mkdir(parents=True)
    (root / TOOLKIT_BUNDLE).replace(root / PACKAGE_BUNDLE)
    (root / TOOLKIT_BUNDLE).parent.rmdir()
    return root


def test_build_is_not_stale():
    assert stale_files(SOURCE, ROOT) == []


def test_gate_4_fails_on_a_changed_extra_or_missing_file(tmp_path):
    built_like_the_script(tmp_path)
    assert stale_files(SOURCE, tmp_path) == []
    (tmp_path / "build" / "svg" / "make-contact.svg").write_text("<svg/>", encoding="utf-8")
    (tmp_path / "build" / "svg" / "no-such-symbol.svg").write_text("<svg/>", encoding="utf-8")
    (tmp_path / "build" / "resolved" / "fuse.json").unlink()
    assert stale_files(SOURCE, tmp_path) == [
        "build/resolved/fuse.json",
        "build/svg/make-contact.svg",
        "build/svg/no-such-symbol.svg",
    ]


def test_gate_4_fails_on_a_changed_or_missing_relocated_bundle(tmp_path):
    built_like_the_script(tmp_path)
    packaged = tmp_path / PACKAGE_BUNDLE
    text = packaged.read_text(encoding="utf-8")
    assert "Fuse" in text
    packaged.write_text(text.replace("Fuse", "Fuze", 1), encoding="utf-8")
    assert stale_files(SOURCE, tmp_path) == [PACKAGE_BUNDLE]
    packaged.unlink()
    assert stale_files(SOURCE, tmp_path) == [PACKAGE_BUNDLE]


def test_gate_4_fails_on_a_bundle_left_at_the_toolkit_path(tmp_path):
    write_build(SOURCE, tmp_path)  # the build without the move
    assert stale_files(SOURCE, tmp_path) == [PACKAGE_BUNDLE, TOOLKIT_BUNDLE]
    (tmp_path / PACKAGE_BUNDLE).parent.mkdir(parents=True)
    shutil.copy(tmp_path / TOOLKIT_BUNDLE, tmp_path / PACKAGE_BUNDLE)
    assert stale_files(SOURCE, tmp_path) == [TOOLKIT_BUNDLE]  # a second copy is still refused


# Gate 5: numbers are unique, match number_pattern and equal the file stems.


def test_numbers_are_unique_match_the_pattern_and_equal_the_stems():
    files = sorted((ROOT / "symbols").glob("*.toml"))
    found = [s.reference.number for s in SOURCE]
    assert len(set(found)) == len(found) == len(files)
    assert numbers(SOURCE) == sorted(p.stem for p in files)
    assert all(re.match(SOURCE.number_pattern, number) for number in found)


# Uniqueness follows from stem equality plus unique file names: two files cannot both be named
# after one number, so a duplicate number always shows up as a stem mismatch.
def test_gate_5_fails_on_a_number_that_differs_from_the_file_stem(tmp_path):
    root = copy_repo(tmp_path, "make-contact")
    edit(root, "make-contact", 'number = "make-contact"', 'number = "fuse"')
    assert problems(root) == [
        (
            "metadata",
            "make-contact.toml: the number 'fuse' differs from the file name 'make-contact'",
        )
    ]


def test_gate_5_fails_on_a_number_that_breaks_the_pattern(tmp_path):
    root = copy_repo(tmp_path, "make-contact")
    edit(root, "make-contact", 'number = "make-contact"', 'number = "mk_contact"')
    shutil.move(root / "symbols" / "make-contact.toml", root / "symbols" / "mk_contact.toml")
    assert problems(root) == [
        (
            "metadata",
            f"mk_contact.toml: the number 'mk_contact' does not match {SOURCE.number_pattern!r}",
        )
    ]


# Gate 6: the packaged bundle holds the same symbols as the source files.


def test_the_bundle_matches_the_source():
    assert numbers(LIBRARY) == numbers(SOURCE)
    assert bundle_problems(LIBRARY, SOURCE) == []


@pytest.mark.parametrize("symbol", list(LIBRARY), ids=ids(list(LIBRARY)))
def test_bundle_symbol_lints_clean(symbol):
    assert lint(symbol) == ()


def bundle_of(root):
    write_build(load_library(root), root)
    return load_bundle(root / TOOLKIT_BUNDLE)  # where write_build puts it, not moved (T1, D39)


def test_gate_6_fails_on_a_bundle_built_from_fewer_symbols(tmp_path):
    bundle = bundle_of(copy_repo(tmp_path, "make-contact"))
    assert "the numbers differ" in bundle_problems(bundle, SOURCE)


def test_gate_6_fails_on_a_bundle_built_from_a_changed_symbol(tmp_path):
    root = copy_repo(tmp_path, "make-contact")
    edit(root, "make-contact", "Make contact, general symbol", "Make contact")
    assert "make-contact differs" in bundle_problems(bundle_of(root), SOURCE)


# TL2 (docs/archive/specs/2026-09-23-terminal-leads.md, spec acceptance 2): the terminal's four stub
# leads are bound to the port each one draws.


def test_terminal_leads_are_bound_to_their_ports():
    terminal = SOURCE.get("terminal")
    bound = {
        e.port: (e.start, e.end)
        for e in terminal.elements
        if isinstance(e, Line) and e.port is not None
    }
    assert set(bound) == {"n", "e", "s", "w"}
    positions = {port.id: port.position for port in terminal.ports}
    for port_id, (start, end) in bound.items():
        assert positions[port_id] in (start, end)


def test_the_built_terminal_json_carries_the_bindings():
    data = json.loads((ROOT / "build" / "resolved" / "terminal.json").read_text(encoding="utf-8"))
    bound = {element["port"] for element in data["elements"] if "port" in element}
    assert bound == {"n", "e", "s", "w"}


@pytest.mark.parametrize("number", ["emergency-stop", "thermal-overload", "rcd"])
def test_protection_symbols_load_with_in_and_out_ports(number):
    """Layout enters a series device at `in` and leaves at `out`, the port ids break-contact has."""
    symbol = LIBRARY.get(number)
    assert {p.id for p in symbol.ports} == {"in", "out"}
    assert any(path.through for path in symbol.paths)


def test_emergency_stop_is_s00258_in_full():
    """Head left of the ports, ring right of the break contact, latching wedge on the link.

    The head is the one Arc, the positive-opening mark the one Circle, the latching wedge
    the one Polyline that leaves the link line (y = 0).
    """
    symbol = SOURCE.get(
        "emergency-stop"
    )  # the source, which the probe patches; the bundle gate ties them
    port_x = {p.position.x for p in symbol.ports}
    arcs = [e for e in symbol.elements if isinstance(e, Arc)]
    circles = [e for e in symbol.elements if isinstance(e, Circle)]
    vees = [
        e
        for e in symbol.elements
        if isinstance(e, Polyline) and any(pt.y != 0 for pt in e.points) and e.points[0].y == 0
    ]
    assert len(arcs) == 1
    assert len(circles) == 1
    assert len(vees) == 1
    assert arcs[0].center.x < min(port_x)
    # the ring sits right of the break contact (its stop ends at x = 1.25), at the link's height
    assert circles[0].center.y == 0
    assert circles[0].center.x - circles[0].radius > 1.25
    # the wedge is on the link, between the head and the link's midpoint
    link = [
        e
        for e in symbol.elements
        if isinstance(e, Line) and e.start.y == e.end.y == 0 and max(e.start.x, e.end.x) <= 0.5
    ]
    link_xs = [pt.x for e in link for pt in (e.start, e.end)]
    midpoint = (min(link_xs) + max(link_xs)) / 2
    wedge_xs = [pt.x for pt in vees[0].points]
    assert arcs[0].center.x < min(wedge_xs)
    assert max(wedge_xs) < midpoint
