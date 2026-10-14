"""Field case: a PLC card that numbers its inputs and outputs from 1 lists two rows, one name.

The engineering shape: one module with a digital input numbered 1 and a digital output numbered
1, as cards that count each direction on its own do.

The bug: a row's channel designation is the module's designation and the channel number only
(`-A1:1`), so the input and the output print the same designation and the list holds two rows
that read alike. The cause: `channel_designation` in `derive/reports.py` (`_plc_channel_row`)
never reads the signal of the channel, so the number alone must be unique per module.

The printed text is the designer's to rule; this case asserts only the rows are told apart.
"""

import fransys as fr
import pytest

from fransys_model.derive import plc_channel_rows

pytestmark = pytest.mark.xfail(strict=True, reason="designer rules the text (LEGACY-B3 L15)")


@pytest.fixture(scope="module")
def built() -> fr.BuildResult:
    d = fr.design("demo_parts", place="C1")
    d.location("C1", "Cabinet")
    d.device("A1", "DEMO-PLC-DIO-1")
    return fr.build(d)


def test_two_channels_of_one_card_have_two_designations(built: fr.BuildResult) -> None:
    rows = plc_channel_rows(built.model)
    assert len(rows) == 2
    assert len({row.channel_designation for row in rows}) == 2
