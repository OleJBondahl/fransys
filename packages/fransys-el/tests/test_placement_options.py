"""The placement conventions and the core options they pass on (E4)."""

import dataclasses
from dataclasses import replace

from fransys_el.placement_options import PLACEMENT_OPTIONS, Conventions, options

from fransys_layout.core import Options, Size


def test_default_options_are_e4_and_otherwise_core_defaults() -> None:
    """The default options spread the box pins, justify and align bands, all else as core."""
    got = options(Conventions())
    assert got.box_pins == "spread"
    assert got.justify is True
    assert got.band_align is True
    core = Options()
    for field in dataclasses.fields(Options):
        if field.name not in ("box_pins", "justify", "band_align"):
            assert getattr(got, field.name) == getattr(core, field.name), field.name


def test_replacing_one_option_moves_only_that_field() -> None:
    """Replacing `row_gap` in `PLACEMENT_OPTIONS` changes exactly that field of the options."""
    base = options(Conventions())
    moved = options(
        dataclasses.replace(Conventions(), options=replace(PLACEMENT_OPTIONS, row_gap=40))
    )
    changed = [
        field.name
        for field in dataclasses.fields(Options)
        if getattr(base, field.name) != getattr(moved, field.name)
    ]
    assert changed == ["row_gap"]
    assert moved.row_gap == 40


def test_default_area_is_the_page_area() -> None:
    """The default page area is 1312 by 854."""
    assert Conventions().area == Size(1312, 854)
