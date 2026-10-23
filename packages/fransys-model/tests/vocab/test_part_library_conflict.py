"""Two versions of one part library name give an ERROR finding that carries its own fix."""

from fransys_model.checks.part_library import PART_LIBRARY_VERSION_CONFLICT, check_part_library
from fransys_model.kernel import Draft, Origin, Severity, freeze, make_id
from fransys_model.vocab.codes import fix_text
from fransys_model.vocab.templates import PartLibrary


def _library(version: str) -> PartLibrary:
    key = ("part_library", "demo-parts", version)
    return PartLibrary(id=make_id(PartLibrary, key), key=key, name="demo-parts", version=version)


def test_a_version_conflict_carries_its_fix() -> None:
    draft = Draft()
    draft.extend((_library("0.1.0"), _library("0.2.0")), origin=Origin(file="<t>", line=1, note=""))
    (finding,) = check_part_library(freeze(draft))
    assert finding.code == PART_LIBRARY_VERSION_CONFLICT
    assert finding.severity is Severity.ERROR
    assert finding.fix == fix_text(PART_LIBRARY_VERSION_CONFLICT)
    assert "Write:" in finding.fix
