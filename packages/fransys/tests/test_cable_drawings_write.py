"""Cable drawings through the facade (cable-drawings spec, Acceptance 10, 15 and 16, facade half).

One SYSTEM document, one drawable top-level two-end cable `W1` (a strip to a motor, `demo_parts`).
The model is built once per variant and the good one is written once, shared by the tests.
"""

import functools

import fransys as fr
import fransys_author
import pytest
from _model_build_cover import _COVER

from fransys_model.derive.cable_drawing import cable_block_key
from fransys_model.vocab import DocumentPreset
from fransys_model.vocab.tables import items

_LONG_TAG = "W" + "L" * 300


def _design(*, extra=None, cable_tag="W1"):
    """A strip `X1` and a motor `M1` joined by `cable_tag`; `extra` adds `W2` or a third core.

    `extra="loop"`: W2 joins two strip terminals (a cable of row links, CD-H8 at V1).
    `extra="shared"`: W1's core 3 lands on the pin its core 1 lands on (CD-H7, until CT5-PIN).
    """
    parts = fr.parts("demo_parts")
    d = fransys_author.Design(parts)
    d.project(title="Cable drawings", number="DEMO-5", customer="Demo Co", revision=1, author="d")
    d.revision(1, date="2026-10-07", text="First issue", created="XX")
    loc = d.location("C1", "Demo cabinet")
    grp = d.group("SUP", "Supply")
    strip = d.strip("X1", at=loc)
    terminals = [strip.terminal("DEMO-TB-2.5", group=grp) for _ in range(4)]
    motor = d.item("DEMO-MOTOR-4KW", tag="M1", at=loc, group=grp)
    cable = d.cable("DEMO-CBL-4G1.5", tag=cable_tag, length_mm=5000)
    cable.core(1, terminals[0].outer, motor["U"])
    cable.core(2, terminals[1].outer, motor["V"])
    if extra == "loop":
        second = d.cable("DEMO-CBL-4G1.5", tag="W2", length_mm=500)
        second.core(1, terminals[2].outer, terminals[3].outer)
    if extra == "shared":
        cable.core(3, terminals[2].outer, motor["U"])
    return parts, d.draft()


@functools.cache
def _built(variant: str):
    kwargs = {
        "good": {},
        "loop": {"extra": "loop"},
        "shared": {"extra": "shared"},
        "wide": {"cable_tag": _LONG_TAG},
    }[variant]
    parts, draft = _design(**kwargs)
    return fr.build(parts, draft, fr.document(DocumentPreset.SYSTEM, None, cover=_COVER))


def _write_good(work):
    return fr.write(_built("good"), work / "out", intermediates=work / "inter"), work / "inter"


@pytest.fixture(scope="module")
def good_written(tmp_path_factory):
    """The good model's write, run once on first call inside a test: `(out files, inter dir)`.

    Called in the test body, so a probe that breaks the write fails the test, not the fixture.
    """
    return functools.cache(lambda: _write_good(tmp_path_factory.mktemp("good")))


def _raised(variant: str, tmp_path):
    """The findings `write` raises for `variant`, with no export and the `.typ` intermediate.

    The intermediates run before the gate: a missing block SVG must not end in a `KeyError` in
    `fransys_pdf.source` (the source leaves the block out, the check reports it).
    """
    with pytest.raises(fr.BuildErrors) as raised:
        fr.write(_built(variant), tmp_path / "out", intermediates=tmp_path / "inter")
    assert not list((tmp_path / "out").glob("*"))
    assert len(list((tmp_path / "inter").glob("*.typ"))) == 1
    return raised.value.findings


def test_write_embeds_the_cable_block_svg_in_the_typst_source(good_written):
    """Acceptance 10, facade half: the SYSTEM `.typ` holds the block as an SVG image, not a table.

    Probe: `_draw_svgs` without `fransys_render.cable_blocks` (no block SVG, the pdf check then
    errors).
    """
    paths, inter = good_written()
    assert any(p.suffix == ".pdf" for p in paths)
    sources = [p.read_text(encoding="utf-8") for p in sorted(inter.glob("*.typ"))]
    assert len(sources) == 1
    assert 'format: "svg"' in sources[0]
    assert sources[0].count('format: "svg"') == 1
    assert "-W1, 5000 mm" in sources[0]  # the block's heading, inside the SVG literal
    assert 'strong(text("Core"))' not in sources[0]  # the old core table's header cell


def test_write_draws_a_cable_of_row_links(tmp_path):
    """CD-H8 at V1, facade half: W2, both core ends on one strip, draws.

    Probe: the engine's `drawable` predicate refusing a cable of row links.
    """
    paths = fr.write(_built("loop"), tmp_path / "out", intermediates=tmp_path / "inter")
    assert any(p.suffix == ".pdf" for p in paths)


def test_write_refuses_a_cable_the_engine_cannot_draw(good_written, tmp_path):
    """Acceptance 16, facade half: two cores on one pin (CD-H7) fail the write.

    The good model (positive control, `good_written`) writes. Probe: the engine's `drawable`
    predicate accepting the shared-pin cable.
    """
    assert good_written()[0]
    findings = _raised("shared", tmp_path)
    missing = [f for f in findings if f.code == "DOCUMENT_NO_DRAWINGS"]
    assert missing
    (w1,) = [i.id for i in items(_built("shared").model).values() if i.key == ("W1",)]
    key = cable_block_key(None, w1)
    assert any(f"missing drawing for {key}" in f.message for f in missing), [
        f.message for f in missing
    ]


def test_write_refuses_a_block_wider_than_the_page(good_written, tmp_path):
    """Acceptance 15, facade half: a block wider than the 1280 G page body fails the write.

    Widened by a 300-character cable tag (`core` takes no label; the heading is the cable's
    designation). The good model (positive control) writes. Probe: pdf's block-size check skipped.
    """
    assert good_written()[0]
    findings = _raised("wide", tmp_path)
    sized = [f for f in findings if f.code == "DOCUMENT_NO_DRAWINGS" and "block" in f.message]
    assert any("the page body holds" in f.message for f in sized), [f.message for f in findings]
