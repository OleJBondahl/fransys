"""Field case: the printed PLC list names a channel's signal in datasheet words.

The engineering shape: a module with a digital input and a digital output (`DEMO-PLC-DIO-1`), a
4-channel analogue input module and a spare output channel no device uses.

The bug: the list printed the enum value (`ai_current`, `di`), which is data, not what a reader
of a datasheet expects.

The rule (decision model-0206, owner H1): `signal_word` maps a signal type to `DI`, `DO`,
`AI (V)`, `AI (mA)`, `AO (V)`, `AO (mA)`, `RTD` or `DO (relay)`; a channel with no function prints
`spare`. The CSV keeps the enum value.
"""

lazy from pathlib import Path

import fransys as fr
import pytest

from fransys_model.derive import plc_channel_rows, plc_list_rows, signal_word
from fransys_model.vocab.enums import SignalType


@pytest.fixture(scope="module")
def built() -> fr.BuildResult:
    d = fr.design("demo_parts", place="C1")
    d.location("C1", "Cabinet")
    d.device("A1", "DEMO-PLC-DIO-1")
    d.device("A2", "DEMO-PLC-AI-4")
    return fr.build(d)


def test_the_list_prints_the_signal_words(built: fr.BuildResult) -> None:
    cells = plc_list_rows(built.model, plc_channel_rows(built.model))
    assert {cell[2] for cell in cells} == {"DI", "DO", "AI (mA)"}


def test_a_channel_with_no_function_prints_spare(built: fr.BuildResult) -> None:
    rows = plc_channel_rows(built.model)
    assert {cells[3] for cells in plc_list_rows(built.model, rows)} == {"spare"}


def test_the_csv_data_keeps_the_enum_value(built: fr.BuildResult) -> None:
    assert {row.signal for row in plc_channel_rows(built.model)} == {
        SignalType.DI,
        SignalType.DO,
        SignalType.AI_CURRENT,
    }


def test_every_signal_type_has_a_word(built: fr.BuildResult) -> None:
    assert {signal_word(built.model, s) for s in SignalType} >= {
        "AI (V)",
        "AO (V)",
        "AO (mA)",
        "RTD",
        "DO (relay)",
    }


def test_a_consumer_word_reaches_the_plc_list(tmp_path: Path) -> None:
    path = tmp_path / "fransys.toml"
    path.write_text('[words]\nsignal_di = "Digital in"\nspare = "free"\n', encoding="utf-8")
    d = fr.design("demo_parts", place="C1")
    d.location("C1", "Cabinet")
    d.device("A1", "DEMO-PLC-DIO-1")
    model = fr.build(d, settings=fr.settings(path)).model
    cells = plc_list_rows(model, plc_channel_rows(model))
    assert {cell[2] for cell in cells} == {"Digital in", "DO"}
    assert {cell[3] for cell in cells} == {"free"}
    assert signal_word(model, SignalType.DI) == "Digital in"
