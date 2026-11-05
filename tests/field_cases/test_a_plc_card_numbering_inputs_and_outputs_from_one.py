"""Field case: a PLC card that numbers its inputs and outputs from 1 lists two rows of one designation.
The bug: a row's channel designation was the module's designation plus the channel number, so input and output printed alike.
Fixed by model-0209, a row is one pin, printed by its port designation, and the two channels sit on different pins."""

import fransys as fr
import pytest

from fransys_model.derive import plc_channel_rows


@pytest.fixture(scope="module")
def built() -> fr.BuildResult:
    d = fr.design("demo_parts", place="C1")
    d.location("C1", "Cabinet")
    d.device("A1", "DEMO-PLC-DIO-1")
    return fr.build(d)


def test_two_channels_of_one_card_have_two_designations(built: fr.BuildResult) -> None:
    rows = plc_channel_rows(built.model)
    assert len(rows) == 2
    assert len({row.pin for row in rows}) == 2
