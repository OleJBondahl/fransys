"""`result.times` names every build step; `write` records the outputs in `intermediates` only.

Decision 0198 (GLASS-BOX G1, G2): the facade times the calls; the times file stays out of `out_dir`.
One module build and two writes serve every test (a PDF compile is slow).
"""

import dataclasses
import json

import fransys as fr
import fransys_author
import pytest
from fransys import DocumentPreset
from fransys._times import BuildTimes, StepTime

_BUILD_STEPS = [
    "merge and freeze",
    "wire rows",
    "PLC allocation",
    "numbering",
    "validators",
    "schematic layout",
    "cable layout",
]


def _design():
    parts = fr.parts("demo_parts")
    d = fransys_author.Design(parts)
    d.project(title="Times", number="T-1", customer="Demo Co", revision=1, author="d")
    d.revision(1, date="2026-10-15", text="First issue", created="XX")
    c1 = d.location("C1", "Demo cabinet")
    sup = d.group("SUP", "Supply")
    strip = d.strip("X1", at=c1)
    t1 = strip.terminal("DEMO-TB-2.5", group=sup)
    q1 = d.item("DEMO-MCB-C6", tag="Q1", at=c1, group=sup)
    d.wiring(colour="BU", gauge="0.75")(t1.inner, q1.fn("element")["1"])
    return parts, d, c1


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    parts, d, c1 = _design()
    cover = tmp_path_factory.mktemp("cover") / "cover.md"
    cover.write_text("# Times\n", encoding="utf-8")
    document = fr.document(DocumentPreset.CABINET_SCHEMATIC, c1, cover=cover)
    return parts, d, document, fr.build(parts, d.draft(), document)


@pytest.fixture(scope="module")
def written(built, tmp_path_factory):
    root = tmp_path_factory.mktemp("written")
    result = built[3]
    fr.write(result, root / "plain")
    fr.write(result, root / "traced", intermediates=root / "inter")
    return root


def test_build_times_name_every_step_in_order(built):
    steps = [s.step for s in built[3].times.steps]
    assert steps == _BUILD_STEPS


def test_times_str_is_one_line_per_step_with_cpu_wall_and_share(built):
    lines = str(built[3].times).splitlines()
    assert len(lines) == len(_BUILD_STEPS)
    assert all("cpu s" in line and "wall s" in line and "% of cpu" in line for line in lines)


def test_two_builds_of_one_design_are_equal(built):
    parts, d, document, first = built
    again = fr.build(parts, d.draft(), document)
    assert again == first


def test_equality_ignores_times(built):
    first = built[3]
    other = BuildTimes((StepTime("forced", 1.0, 2.0),))
    assert other != first.times
    assert dataclasses.replace(first, times=other) == first


def test_write_puts_times_file_in_intermediates_only(written):
    data = json.loads((written / "inter" / "build-times.json").read_text(encoding="utf-8"))
    steps = [row["step"] for row in data["steps"]]
    assert steps[: len(_BUILD_STEPS)] == _BUILD_STEPS
    assert any(step.endswith(".pdf") for step in steps[len(_BUILD_STEPS) :])
    assert any(step.endswith("bom.csv") for step in steps[len(_BUILD_STEPS) :])
    assert not list((written / "plain").rglob("build-times.json"))
    assert not list((written / "traced").rglob("build-times.json"))


def test_out_dir_is_byte_identical_with_and_without_intermediates(written):
    def tree(folder):
        return {p.relative_to(folder): p.read_bytes() for p in folder.rglob("*") if p.is_file()}

    plain, traced = tree(written / "plain"), tree(written / "traced")
    assert plain
    assert plain.keys() == traced.keys()
    assert plain == traced
