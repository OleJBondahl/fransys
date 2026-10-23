"""A consumer's `[stub]`, `[wire_label]` and `[harness]` keys reach the printed text (SO2)."""

lazy from pathlib import Path

import pytest

from fransys_model.derive.drawing_text import wire_text
from fransys_model.derive.house_settings import harness_text_of, stub_text_of
from fransys_model.derive.stub_text import off_stub_line
from fransys_model.vocab.tables import conductors

from ._settings_text_builds import consumer_file, skid_model

pytestmark = pytest.mark.wp("facade")


def test_a_stub_arrow_and_port_signs_are_the_consumers(tmp_path: Path) -> None:
    ours = stub_text_of(skid_model())
    form = stub_text_of(
        skid_model(
            consumer_file(tmp_path, '[stub]\narrow_out = ">"\nport_sep = "/"\nport_join = ","\n')
        )
    )
    assert off_stub_line(ours, "-W3", north=False, far="+EXT-K1", ports=(":1", ":2")) == (
        "-W3 → +EXT-K1:1 2"
    )
    assert off_stub_line(form, "-W3", north=False, far="+EXT-K1", ports=(":1", ":2")) == (
        "-W3 > +EXT-K1/1,2"
    )
    assert form.arrow_in == ours.arrow_in


def test_a_wire_label_separator_is_the_consumers(tmp_path: Path) -> None:
    model = skid_model(consumer_file(tmp_path, '[wire_label]\nseparator = "/"\n'))
    first = next(iter(conductors(model)))
    assert wire_text(skid_model(), first) == "-F14:5 -Q4:6"
    assert wire_text(model, first) == "-F14:5/-Q4:6"


def test_a_wire_label_may_show_one_end(tmp_path: Path) -> None:
    model = skid_model(consumer_file(tmp_path, "[wire_label]\nshow_ends = false\n"))
    assert wire_text(model, next(iter(conductors(model)))) == "-F14:5"


def test_a_harness_branch_sign_is_the_consumers(tmp_path: Path) -> None:
    model = skid_model(consumer_file(tmp_path, '[harness]\nbranch_sep = "_"\n'))
    assert harness_text_of(model).branch_sep == "_"
    assert harness_text_of(skid_model()).branch_sep == "."
