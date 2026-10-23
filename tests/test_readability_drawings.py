"""`fr.readability` counts the build's `BuildResult.drawings`, laying nothing out (R218, R255)."""

import dataclasses

import fransys as fr
import fransys_el
from _motor_feeder_case import motor_feeder_case_drafts


def test_readability_reads_the_build_drawings() -> None:
    result = fr.build(*motor_feeder_case_drafts())
    reading = fr.readability(result)
    assert reading == fransys_el.readability(result.drawings)
    assert len(reading.pages) == len(result.drawings) > 0


def test_empty_drawings_give_zero_pages() -> None:
    """The error-build case (R249): no drawings, no rows, no refusal."""
    result = dataclasses.replace(fr.build(*motor_feeder_case_drafts()), drawings={})
    assert fr.readability(result).pages == ()
