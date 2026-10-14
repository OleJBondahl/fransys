"""Field case: a PLC card that numbers its inputs and outputs from 1 lists two rows, one name.

The engineering shape: one module with a digital input numbered 1 and a digital output numbered
1, as cards that count each direction on its own do.

The bug: a row's channel designation was the module's designation and the channel number only
(`-A1:1`), so the input and the output printed the same designation and the list held two rows
that read alike. The cause: `channel_designation` in `derive/reports.py` never read the signal
of the channel, so the number alone had to be unique per module.

The fix is decision model-0209: a row is one pin, printed by its port designation, and the two
channels sit on different pins. The Ch column still reads 1 for both; the pins tell them apart.
"""

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
