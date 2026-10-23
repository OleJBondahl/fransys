"""The words a printed PLC list uses for a channel's signal and for a channel with no function.

Both come from the model's `[words]` record (`signal_*` keys and `spare`).

Reached as `derive.signal_word` and `derive.plc_list_rows` (model-0206). The CSV keeps the
enum value, because it is data; every page that prints a signal kind calls `signal_word`.
"""

lazy from collections.abc import Iterable

from fransys_model.vocab.enums import SignalType
lazy from fransys_model.kernel import Model

from .facts.house_settings import word
lazy from .columns import PLC_COLUMNS
lazy from .rows_plc import PlcChannelRow

__all__ = ["plc_list_rows", "signal_word"]

_KEYS = {
    SignalType.DI: "signal_di",
    SignalType.DO: "signal_do",
    SignalType.AI_CURRENT: "signal_ai_ma",
    SignalType.AI_VOLTAGE: "signal_ai_v",
    SignalType.AO_CURRENT: "signal_ao_ma",
    SignalType.AO_VOLTAGE: "signal_ao_v",
    SignalType.RTD: "signal_rtd",
    SignalType.RELAY: "signal_relay_do",
}


def signal_word(model: Model, signal: SignalType) -> str:
    """The word `[words]` gives `signal`.

    Our defaults are `DI`, `DO`, `AI (V)`, `AI (mA)`, `AO (V)`, `AO (mA)`, `RTD` and `DO (relay)`.
    """
    return word(model, _KEYS[signal])


def plc_list_rows(
    model: Model,
    rows: Iterable[PlcChannelRow],
) -> tuple[tuple[str | None, ...], ...]:
    """One `PLC_COLUMNS` line per row for a printed list: the signal as its word.

    A channel bound to no field device and wired to nothing prints the `spare` word for its
    signal name. The cells follow `PLC_COLUMNS`' order, so a column change edits that tuple alone.
    """
    return tuple(_plc_cells(model, row) for row in rows)


def _plc_cells(model: Model, row: PlcChannelRow) -> tuple[str | None, ...]:
    spare = row.field_device is None and row.wired_to is None
    cells: dict[str, str | None] = {
        "pin": row.pin,
        "channel_name": row.channel_name,
        "signal": signal_word(model, row.signal),
        "wired_to": row.wired_to,
        "signal_name": word(model, "spare") if spare else row.signal_name,
    }
    return tuple(cells[column] for column in PLC_COLUMNS)
