"""Decision 0104, rule D: which WARNINGs a unit release's manifest lists.

A unit release keeps a WARNING when one of its subjects of an owned kind (item, function, port,
unit, document) is inside the unit (its subtree, or a document it exports), or when it has no
subject of an owned kind. A system release keeps every WARNING. One system build of two sibling
units serves the filter tests (a module fixture); each acceptance case names its probe.
"""

import json
lazy from pathlib import Path

import fransys as fr
import fransys_author
import pytest
from fransys._release_manifest import _warning_entries

from fransys_model.derive import document_unit, unit_items
from fransys_model.kernel import Finding, Severity
from fransys_model.vocab import documents, functions, items, ports

_NEW = "DESIGNATION_NEW_IN_REVISION"
_DATE = "2026-10-05"


def _sibling(design, name, *, cable):
    """One unit `name` with a board, a relay and (when `cable`) a core-less 4-core cable."""
    u = design.scope(name).unit(name, revision=1, interface="1")
    u.revision(1, date=_DATE, text="First", created="OJB")
    board = u.item("DEMO-PCB-IO", name="board")
    relay = u.item("DEMO-RLY-2CO-24", name="k1", parent=board)
    if cable:
        u.cable("DEMO-CBL-4G1.5", name="w1c", parent=board)
    return u, relay


@pytest.fixture(scope="module")
def system(tmp_path_factory):
    """`(result, scope_a, scope_b, into)`: two sibling units, a net with an undeclared potential."""
    parts = fr.parts("demo_parts")
    design = fransys_author.Design(parts)
    scope_a, relay_a = _sibling(design, "mw-a", cable=False)
    scope_b, _relay_b = _sibling(design, "mw-b", cable=True)
    design.net("mw-net", relay_a.fn("coil")["A1"], potential="+99V")
    covers = tmp_path_factory.mktemp("covers")
    docs = []
    for name, scope in (("a", scope_a), ("b", scope_b)):
        cover = covers / f"{name}.md"
        cover.write_text("# Cover\n", encoding="utf-8")
        docs.append(fr.document(fr.DocumentPreset.PCB_SCHEMATIC, scope, cover=cover))
    result = fr.build(parts, design.draft(), *docs)
    assert [f for f in fr.check(result) if f.severity is fr.Severity.ERROR] == []
    return result, scope_a, scope_b, tmp_path_factory.mktemp("releases")


@pytest.fixture(scope="module")
def manifest_a(system):
    """Unit A released from the system build: its manifest, and the model's own raw findings."""
    result, scope_a, _scope_b, into = system
    target = fr.release(result, into, unit=scope_a)
    return json.loads((target / "baseline" / "manifest.json").read_text(encoding="utf-8"))


def _item(model, unit_scope, name):
    (found,) = [i for i in unit_items(model, unit_scope.unit_id) if items(model)[i].key[-1] == name]
    return found


def _port(model, unit_scope):
    inside = unit_items(model, unit_scope.unit_id)
    fns = {f for f, fn in functions(model).items() if fn.item in inside}
    return min(p for p, port in ports(model).items() if port.function in fns)


def _document_of(model, unit_scope):
    (found,) = [
        i for i, r in documents(model).items() if document_unit(model, r) == unit_scope.unit_id
    ]
    return found


def _warn(code, *subjects):
    return Finding(code=code, severity=Severity.WARNING, subjects=subjects, message=code)


def _codes(entries):
    return [e["code"] for e in entries]


# -- acceptance 1: an untagged new instance is listed with its listing text ----------------


@pytest.fixture
def released(tmp_path: Path) -> Path:
    """A cabinet of two floating board instances, released at revision 1."""
    result, cab, board = _cabinet(1, ("m1", "m2"))
    fr.release(result, tmp_path, unit=board)
    fr.release(result, tmp_path, unit=cab)
    return tmp_path


def _cabinet(revision, boards, releases=None):
    parts = fr.parts("demo_parts")
    design = fransys_author.Design(parts)
    cab = design.scope("cab").unit("mw-cabinet", revision=revision, interface="1", class_code="U")
    cab.revision(revision, date=_DATE, text=f"Revision {revision}", created="OJB")
    board = None
    for name in boards:
        board = cab.scope(name).unit("mw-board", revision=1, interface="1", class_code="U")
        board.revision(1, date=_DATE, text="First", created="OJB")
        board.item("DEMO-PCB-IO", name="pcb")
    return fr.build(parts, design.draft(), releases=releases), cab, board


def test_a_new_untagged_instance_is_listed_by_its_listing_text(released: Path) -> None:
    """Probe: restore the old `set(finding.subjects) & relevant` filter."""
    result, cab, _ = _cabinet(2, ("m1", "m2", "m3"), releases=released)
    target = fr.release(result, released, unit=cab)
    manifest = json.loads((target / "baseline" / "manifest.json").read_text(encoding="utf-8"))
    listed = [w["subjects"] for w in manifest["warnings"] if w["code"] == _NEW]
    assert listed == [["-U3"]]


# -- acceptance 2: a sibling unit's item warning is not listed --------------------------------


def test_a_sibling_units_item_warning_is_not_listed(system) -> None:
    """Probe: drop the filter (keep every WARNING)."""
    result, scope_a, scope_b, _into = system
    model = result.model
    own = _warn("OWN_ITEM", _item(model, scope_a, "k1"))
    sibling = _warn("SIBLING_ITEM", _item(model, scope_b, "k1"))
    assert _codes(_warning_entries(model, scope_a.unit_id, (own, sibling))) == ["OWN_ITEM"]


def test_a_system_release_keeps_every_warning(system) -> None:
    result, scope_a, scope_b, _into = system
    model = result.model
    both = (
        _warn("A", _item(model, scope_a, "k1")),
        _warn("B", _item(model, scope_b, "k1")),
    )
    assert _codes(_warning_entries(model, None, both)) == ["A", "B"]


# -- acceptance 3: a sibling's cable (cable + product) is not listed, and nothing raises -------


def test_a_siblings_short_cable_is_not_listed_and_the_release_does_not_raise(
    system, manifest_a
) -> None:
    """Probe: the looser rule, keep a WARNING when any subject is of an unowned kind."""
    result, scope_a, _scope_b, _into = system
    raw = [f for f in fr.check(result) if f.code == "CABLE_CORE_COUNT"]
    assert raw, "the sibling's core-less cable warns in the system build"
    assert len(raw[0].subjects) == 2, "the cable and its product"
    assert "CABLE_CORE_COUNT" not in _codes(manifest_a["warnings"])
    assert _codes(_warning_entries(result.model, scope_a.unit_id, tuple(raw))) == []


# -- acceptance 4: a net-only warning is listed ----------------------------------------------


def test_a_net_only_warning_is_listed_in_a_unit_release(manifest_a) -> None:
    """Probe: the old `set(finding.subjects) & relevant` filter."""
    listed = [
        w["subjects"] for w in manifest_a["warnings"] if w["code"] == "POTENTIAL_WITHOUT_SUPPLY"
    ]
    assert listed == [["net/mw-net"]]


# -- acceptance 5: the unit's own document warning is listed, a sibling's is not ----------------


def test_the_units_own_document_warning_is_listed(system) -> None:
    """Probe: the old filter (documents were never owned)."""
    result, scope_a, _scope_b, _into = system
    finding = _warn("OWN_DOC", _document_of(result.model, scope_a))
    assert _codes(_warning_entries(result.model, scope_a.unit_id, (finding,))) == ["OWN_DOC"]


def test_a_sibling_documents_warning_is_not_listed(system) -> None:
    """Probe: treat a document as unowned (keep it): the sibling's warning appears."""
    result, scope_a, scope_b, _into = system
    finding = _warn("SIBLING_DOC", _document_of(result.model, scope_b))
    assert _warning_entries(result.model, scope_a.unit_id, (finding,)) == []


def test_a_warning_with_an_owned_and_a_foreign_subject_is_kept_by_the_owned_one(system) -> None:
    result, scope_a, scope_b, _into = system
    model = result.model
    mixed = _warn("MIXED", _item(model, scope_b, "k1"), _item(model, scope_a, "k1"))
    assert _codes(_warning_entries(model, scope_a.unit_id, (mixed,))) == ["MIXED"]


def test_a_port_is_owned_by_its_unit(system) -> None:
    result, scope_a, scope_b, _into = system
    model = result.model
    own, other = (
        _warn("OWN_PORT", _port(model, scope_a)),
        _warn("OTHER_PORT", _port(model, scope_b)),
    )
    assert _codes(_warning_entries(model, scope_a.unit_id, (own, other))) == ["OWN_PORT"]


def test_a_warning_on_the_released_unit_itself_is_kept_and_renders(system) -> None:
    """The release's own unit is a subject inside its subtree; its text is its key, not a crash."""
    result, scope_a, _scope_b, _into = system
    finding = _warn("OWN_UNIT", scope_a.unit_id)
    (entry,) = json.loads(json.dumps(_warning_entries(result.model, scope_a.unit_id, (finding,))))
    assert entry["subjects"] == ["mw-a/unit"]


def _nested(*, outer_tag, inner_tag):
    """`(model, outer, mid, inner)`: an outer unit holding a tagged-or-not mid holding an inner."""
    parts = fr.parts("demo_parts")
    design = fransys_author.Design(parts)
    outer = design.scope("out").unit("mw-outer", revision=1, interface="1")
    outer.revision(1, date=_DATE, text="First", created="OJB")
    mid = outer.scope("mid").unit("mw-mid", revision=1, interface="1", tag=outer_tag)
    mid.revision(1, date=_DATE, text="First", created="OJB")
    inner = mid.scope("inn").unit("mw-inner", revision=1, interface="1", tag=inner_tag)
    inner.revision(1, date=_DATE, text="First", created="OJB")
    inner.item("DEMO-PCB-IO", name="pcb")
    model = fr.build(parts, design.draft()).model
    return model, outer.unit_id, mid.unit_id, inner.unit_id


def _text(model, unit, subject):
    finding = _warn("INSTANCE", subject)
    (entry,) = json.loads(json.dumps(_warning_entries(model, unit, (finding,))))
    return entry["subjects"][0]


def test_a_nested_tagged_instance_prints_the_whole_tag_chain() -> None:
    """Probe: join only the innermost tag (`-U3`)."""
    model, outer, mid, inner = _nested(outer_tag="U1", inner_tag="U3")
    assert _text(model, outer, inner) == "-U1-U3"
    assert _text(model, outer, mid) == "-U1"


def test_an_untagged_middle_link_prints_the_key_below_the_unit_never_a_partial_chain() -> None:
    """Probe: drop an untagged link from the chain (`-U3` hides the middle instance)."""
    model, outer, _mid, inner = _nested(outer_tag=None, inner_tag="U3")
    assert _text(model, outer, inner) == "mid/inn/unit"


def test_an_untagged_instance_prints_its_key_below_the_unit() -> None:
    model, outer, mid, _inner = _nested(outer_tag=None, inner_tag=None)
    assert _text(model, outer, mid) == "mid/unit"
