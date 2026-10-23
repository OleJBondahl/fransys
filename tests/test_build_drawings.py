"""A `BuildResult` carries the drawings its build laid out (FLIP-NOW F7, el-0039, R223/R240).

`build` lays out once and keeps the page Drawings on the result's `drawings` field; `check`,
`write` and `release` read them from the result they get. The SVGs and the pdf links equal what
a fresh `lay_out_drawn` run and `reference_links` give.
"""

import dataclasses
import importlib.util
from pathlib import Path

import fransys as fr
import pytest
from _direct_case import built_with_unlaid, laid_again
from _motor_feeder_case import motor_feeder_case_drafts
from fransys import _layout_core, pipeline
from fransys_el import style
from fransys_render import svg

from electrical_symbols import LIBRARY
from fransys_model.derive.page_nav import reference_links
from fransys_model.kernel import render_id
from fransys_model.layout import Page, layout_of

SKID = Path(__file__).resolve().parent.parent / "examples" / "demo-skid" / "skid.py"


def _skid_drafts() -> tuple:
    spec = importlib.util.spec_from_file_location("demo_skid_laid", SKID)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.design()


@pytest.fixture(scope="module")
def skid(tmp_path_factory):
    result, unlaid = built_with_unlaid(lambda: fr.build(*_skid_drafts()))
    folder = tmp_path_factory.mktemp("skid")
    fr.write(result, folder / "out", intermediates=folder / "mid")
    return result, folder / "mid", unlaid


def _fresh_svgs(model, unlaid) -> dict[str, str]:
    """The SVGs of a fresh `lay_out_drawn` run over the model the facade handed the core."""
    look = style(LIBRARY)
    drawn = laid_again(unlaid)[1]
    return {
        render_id(page).replace(":", "-"): svg(
            drawing, LIBRARY, look, sheet_mm=_layout_core._sheet_mm(model, page)
        )
        for page, drawing in drawn.items()
    }


def test_the_written_page_svgs_equal_a_fresh_run(skid):
    result, mid, unlaid = skid
    old = _fresh_svgs(result.model, unlaid)
    assert old
    for name, text in old.items():
        assert (mid / f"{name}.svg").read_text(encoding="utf-8") == text


def test_the_svg_comparison_can_fail(skid):
    result, mid, unlaid = skid
    name, text = next(iter(_fresh_svgs(result.model, unlaid).items()))
    assert (mid / f"{name}.svg").read_text(encoding="utf-8") != text + " "


def test_the_pdf_links_equal_reference_links(tmp_path, monkeypatch):
    result = fr.build(*motor_feeder_case_drafts(8))
    seen = []

    real = pipeline.fransys_pdf.source

    def spy(*args, **kwargs):
        seen.append(kwargs["links"])
        return real(*args, **kwargs)

    monkeypatch.setattr(pipeline.fransys_pdf, "source", spy)
    model = result.model
    # `write` would refuse this 8-starter case on the old `render.check`; the sources come first
    pipeline._write_intermediates(
        model,
        result.drawings,
        pipeline._svgs(model, result.drawings),
        tmp_path,
        result.settings.pdf,
    )
    known = set(layout_of(model, Page))
    expected = {page: reference_links(model, page, known) for page in known}
    assert sum(len(found) for found in expected.values()) == 2
    assert seen
    assert all(links == expected for links in seen)


def test_a_result_kept_across_many_later_builds_still_writes(tmp_path):
    first = fr.build(*motor_feeder_case_drafts(3))
    for count in range(1, 10):
        fr.build(*motor_feeder_case_drafts(count % 4 + 1))
    assert fr.write(first, tmp_path / "out", intermediates=tmp_path / "mid")
    assert list((tmp_path / "mid").glob("*.svg"))


def test_the_layout_solves_once_per_build(tmp_path, monkeypatch):
    calls = []
    real = _layout_core.lay_out_drawn

    def counted(*args):
        calls.append(1)
        return real(*args)

    monkeypatch.setattr(_layout_core, "lay_out_drawn", counted)
    result = fr.build(*motor_feeder_case_drafts(3))
    fr.check(result)
    fr.write(result, tmp_path / "out", intermediates=tmp_path / "mid")
    assert len(calls) == 1


def test_build_result_fields_are_unchanged_but_for_drawings():
    assert [f.name for f in dataclasses.fields(fr.BuildResult)] == [
        "model",
        "findings",
        "settings",
        "times",
        "drawings",
    ]


def test_repr_and_equality_ignore_the_drawings():
    result = fr.build(*motor_feeder_case_drafts(3))
    assert result.drawings
    bare = dataclasses.replace(result, drawings={})
    assert bare == result
    assert "drawings" not in repr(result)
