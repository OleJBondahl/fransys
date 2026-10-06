"""Decision 0054: `pipeline._svgs` memoises `_draw_svgs` on `model.digest`, last model only.

Without the memo, `write`/`check`/`release` would each re-render every schematic page for a
model whose digest has not changed, for no reason; without the fresh-copy wrapper, one caller
could mutate the dict the memo hands to the next caller. Both properties are checked here
against the real drawing path (a document with a top-level cable and a rendered schematic
page), not against a stub.
"""

import fransys as fr
import fransys_author
import fransys_render
import pytest
from demo_designs import cabinet_design
from fransys import pipeline


def _spy(monkeypatch, module, name):
    """Wrap `module.name` in a call-counting delegate to the real function."""
    calls: list[tuple] = []
    original = getattr(module, name)

    def wrapper(*args, **kwargs):
        calls.append((args, kwargs))
        return original(*args, **kwargs)

    monkeypatch.setattr(module, name, wrapper)
    return calls


def _document_build(parts, cover_dir, text="# Demo cabinet\n"):
    """The demo cabinet design plus a `CABINET_SCHEMATIC` document over its own location.

    Same shape as `test_model_only_build.py::_document_build`: the document gives a rendered
    schematic page for `_draw_svgs` to draw.
    """
    design = cabinet_design(parts)
    c1 = fransys_author.Design(parts).location("C1", "Demo cabinet")
    cover = cover_dir / "cabinet.md"
    cover.write_text(text, encoding="utf-8")
    document_draft = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, c1, cover=cover)
    return fr.build(parts, design.draft(), document_draft)


@pytest.fixture(scope="module")
def result(tmp_path_factory) -> fr.BuildResult:
    """The document build above, built once and shared (BUILD-ONCE): checked clean here so
    every test below can assume a real draw, never an early findings-gate exit.
    """
    parts = fr.parts("demo_parts")
    cover_dir = tmp_path_factory.mktemp("cover")
    built = _document_build(parts, cover_dir)
    findings = fr.check(built)
    assert not any(f.severity is fr.Severity.ERROR for f in findings), findings
    return built


@pytest.fixture(autouse=True)
def _cold_memo():
    """Clear the digest memo before every test: each test starts with nothing drawn yet."""
    pipeline._svgs_cache.cache_clear()


def test_two_writes_of_the_same_result_draw_only_once(result, tmp_path, monkeypatch):
    """Two `write`s of one model share the one draw the memo holds (decision 0054): without
    it, the second write would render again for a digest already drawn.
    """
    calls = _spy(monkeypatch, fransys_render, "pages")

    first = fr.write(result, tmp_path / "out1", unit=None)
    second = fr.write(result, tmp_path / "out2", unit=None)

    assert len(calls) == 1
    assert first, "sanity: the first write produced files"
    assert second, "sanity: the second write produced files"


def test_a_changed_model_draws_again(result, tmp_path, monkeypatch):
    """A model with a different digest is not served the stale memo: `render.pages` runs once
    per distinct digest, twice here for two digests, never once for both.
    """
    parts = fr.parts("demo_parts")
    cover_dir = tmp_path / "changed_cover"
    cover_dir.mkdir()
    changed = _document_build(parts, cover_dir, text="# Demo cabinet v2\n")
    assert changed.model.digest != result.model.digest, "the perturbed cover must change the digest"

    calls = _spy(monkeypatch, fransys_render, "pages")

    fr.write(result, tmp_path / "out1", unit=None)
    fr.write(changed, tmp_path / "out2", unit=None)

    assert len(calls) == 2


def test_memoised_and_unmemoised_writes_give_byte_equal_files(result, tmp_path):
    """The memo is an optimisation, not a second code path: a cached draw and a forced fresh
    draw of the same model must write identical bytes (same idiom as
    `test_acceptance.py::test_two_writes_of_one_result_give_byte_equal_files`).
    """
    first = fr.write(result, tmp_path / "out1")
    pipeline._svgs_cache.cache_clear()
    second = fr.write(result, tmp_path / "out2")

    assert {p.name for p in first} == {p.name for p in second}
    for path in first:
        twin = tmp_path / "out2" / path.name
        assert twin.read_bytes() == path.read_bytes()


def test_svgs_hands_out_a_fresh_copy_every_call(result):
    """`_svgs` returns `dict(_svgs_cache(model))`, a copy, every call: a caller that mutates
    what it got back must never affect the memo's held value or a later caller's dict.
    """
    svgs1 = pipeline._svgs(result.model)
    real_keys = set(svgs1)
    svgs1["bogus"] = "x"
    svgs1.clear()

    svgs2 = pipeline._svgs(result.model)

    assert svgs2 is not svgs1
    assert set(svgs2) == real_keys
    assert "bogus" not in svgs2
