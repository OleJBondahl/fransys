"""The words a printed PLC list uses for a channel's signal and for a channel with no function.

Reached as `derive.signal_word` and `derive.plc_list_rows` (model-0206). The CSV keeps the
enum value, because it is data; every page that prints a signal kind calls `signal_word`.
"""

lazy from collections.abc import Iterable

from fransys_model.vocab.enums import SignalType

lazy from .columns import PLC_COLUMNS
lazy from .rows import PlcChannelRow

__all__ = ["SPARE_WORD", "plc_list_rows", "signal_word"]

SPARE_WORD = "spare"
_WORDS = {
    SignalType.DI: "DI",
    SignalType.DO: "DO",
    SignalType.AI_CURRENT: "AI (mA)",
    SignalType.AI_VOLTAGE: "AI (V)",
    SignalType.AO_CURRENT: "AO (mA)",
    SignalType.AO_VOLTAGE: "AO (V)",
    SignalType.RTD: "RTD",
    SignalType.RELAY: "DO (relay)",
}


def signal_word(signal: SignalType) -> str:
    """The datasheet word for `signal`: `DI`, `DO`, `AI (V)`, `AI (mA)`, `AO (V)`, `AO (mA)`, `RTD`.

    A relay output prints `DO (relay)`.
    """
    return _WORDS[signal]


def plc_list_rows(
    rows: Iterable[PlcChannelRow],
) -> tuple[tuple[str | None, ...], ...]:
    """One `PLC_COLUMNS` line per row for a printed list: the signal as its word.

    A channel bound to no field device and wired to nothing prints `spare` for its signal name.
    The cells follow `PLC_COLUMNS`' order, so a column change edits that tuple alone.
    """
    return tuple(_plc_cells(row) for row in rows)


def _plc_cells(row: PlcChannelRow) -> tuple[str | None, ...]:
    cells: dict[str, str | None] = {
        "channel_designation": row.channel_designation,
        "signal": signal_word(row.signal),
        "wired_to": row.wired_to,
        "signal_name": (
            SPARE_WORD if row.field_device is None and row.wired_to is None else row.signal_name
        ),
    }
    return tuple(cells[column] for column in PLC_COLUMNS)
