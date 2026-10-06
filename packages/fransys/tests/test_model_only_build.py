"""PS1/PS2: `build`/`check`/`write` run layout only when the frozen model holds a `Document`.

Layout exists only to draw documents. With no document there is nothing to draw, so `fr.build`
returns the numbered, validated model unlaid, with no layout call attempted -- no flag, no new
function (docs/archive/specs/2026-09-26-public-model-build.md). Every absence assertion below is
paired with the positive case that proves the same mechanism can produce the opposite result
(root CLAUDE.md's field-cases convention, applied here to a unit test rather than a field case).
"""

import fransys as fr
import fransys_author
import fransys_pdf
import fransys_render
import pytest
from demo_designs import cabinet_design
from fransys import pipeline

_GATED_PIPELINE_NAMES = ("lay_out_schematic",)


def _spy(monkeypatch, module, name):
    """Wrap `module.name` in a call-counting delegate to the real function."""
    calls: list[tuple] = []
    original = getattr(module, name)

    def wrapper(*args, **kwargs):
        calls.append((args, kwargs))
        return original(*args, **kwargs)

    monkeypatch.setattr(module, name, wrapper)
    return calls


def _spy_every_gated_call(monkeypatch):
    """One call list per function PS1/PS2 gates, keyed by name."""
    calls = {name: _spy(monkeypatch, pipeline, name) for name in _GATED_PIPELINE_NAMES}
    calls["fransys_pdf.check"] = _spy(monkeypatch, fransys_pdf, "check")
    calls["fransys_render.check"] = _spy(monkeypatch, fransys_render, "check")
    calls["fransys_render.pages"] = _spy(monkeypatch, fransys_render, "pages")
    return calls


def _no_document_build(parts):
    """The demo cabinet design, no document draft at all."""
    design = cabinet_design(parts)
    return fr.build(parts, design.draft())


def _document_build(parts, tmp_path):
    """The same design, plus a `CABINET_SCHEMATIC` document over its own location.

    `cabinet_design`'s own top-level cable (`demo_designs.py` line 43, `d.cable(...)`, not
    inside a harness) gives this build a rendered `SCHEMATIC` page to make that
    `_no_document_build` never makes, so the two are a real positive/negative pair, not just
    "one has a document record".
    """
    design = cabinet_design(parts)
    c1 = fransys_author.Design(parts).location("C1", "Demo cabinet")
    cover = tmp_path / "cabinet.md"
    cover.write_text("# Demo cabinet\n", encoding="utf-8")
    document_draft = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, c1, cover=cover)
    return fr.build(parts, design.draft(), document_draft)


def test_no_document_build_runs_no_layout_or_render(tmp_path, monkeypatch):
    parts = fr.parts("demo_parts")
    calls = _spy_every_gated_call(monkeypatch)

    result = _no_document_build(parts)
    fr.check(result)
    fr.write(result, tmp_path / "out", intermediates=tmp_path / "inter")

    counts = {name: len(hits) for name, hits in calls.items()}
    assert counts == dict.fromkeys(calls, 0)


def test_document_build_runs_layout_and_render(tmp_path, monkeypatch):
    """The positive counterpart: a document over a location with a top-level cable makes
    `build`/`check`/`write` call every function the test above proves is skipped without one.
    """
    parts = fr.parts("demo_parts")
    # `_document_build` is deterministic (same digest every call, decision 0054); clear the
    # memo so this call is a real draw, not a hit left warm by an earlier test in this process
    # (no autouse clear covers this any more, FIX1).
    pipeline._svgs_cache.cache_clear()
    calls = _spy_every_gated_call(monkeypatch)

    result = _document_build(parts, tmp_path)
    fr.check(result)
    fr.write(result, tmp_path / "out", intermediates=tmp_path / "inter")

    assert len(calls["lay_out_schematic"]) > 0
    assert len(calls["fransys_pdf.check"]) > 0
    assert len(calls["fransys_render.check"]) > 0
    assert len(calls["fransys_render.pages"]) > 0


def _changeover_no_document_draft(parts):
    """The changeover field case's `in_unit=True` design (poles 3 and 4 routed to two field
    strips), with no document draft -- the same shape as
    `tests/field_cases/test_changeover_throws_to_two_strips.py::_build(in_unit=True)`.
    """
    design = fransys_author.Design(parts)
    scope = design.scope("unit").unit("unit", revision=1, interface="1")
    scope.revision(1, date="2026-09-26", text="First issue", created="XX")
    cab = scope.location("CAB", "Cabinet")
    field = scope.location("FIELD", "Field strips")
    supply = scope.group("SUP", "Supply")
    field_a = scope.strip("X01", at=field)
    field_b = scope.strip("X02", at=field)
    relay = scope.item("DEMO-CO-4P-24", tag="K1", at=cab, group=supply)
    wire = scope.wiring(colour="BK", gauge="1.5")
    for pole in (3, 4):
        make = field_a.terminal("DEMO-TB-2.5", f"RUN{pole}", group=supply)
        brk = field_b.terminal("DEMO-TB-2.5", f"RUN{pole}", group=supply)
        fn = relay.fn(f"co_{pole}")
        wire(brk.inner, fn[f"{pole}2"])
        wire(make.inner, fn[f"{pole}4"])
    return design.draft()


def test_no_document_build_does_not_raise_but_a_document_build_does(tmp_path, monkeypatch):
    """Can-fail proof: a raise planted in every gated layout call never fires for a
    document-free build, and fires for the same shape of build once a document is added.
    """

    def _raiser(*_args, **_kwargs):
        message = "a layout call ran on a build that should have skipped it"
        raise AssertionError(message)

    for name in _GATED_PIPELINE_NAMES:
        monkeypatch.setattr(pipeline, name, _raiser)

    parts = fr.parts("demo_parts")
    no_document_result = fr.build(parts, _changeover_no_document_draft(parts))
    assert isinstance(no_document_result, fr.BuildResult), "no raise for a document-free build"

    # `_document_build` is deterministic (same digest every call, decision 0054); clear the
    # memo so the raise below fires from a real (gated) call, not a hit that skips the gated
    # function entirely and so never raises (no autouse clear covers this any more, FIX1).
    pipeline._svgs_cache.cache_clear()
    with pytest.raises(AssertionError, match="ran on a build that should have skipped it"):
        _document_build(parts, tmp_path)
