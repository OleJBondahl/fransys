"""Tests: the signal-type table is complete and `signal_kind` reproduces the old mapping."""

import dataclasses

import pytest

from fransys_model.derive import signal_kind
from fransys_model.derive.rows_plc import SignalKind
from fransys_model.vocab.enums import SignalType
from fransys_model.vocab.roles_types import complete
from fransys_model.vocab.signal_types import SIGNAL_TYPES

_S, _K = SignalType, SignalKind
_OLD = {
    _S.DI: _K.DIGITAL_IN,
    _S.DO: _K.DIGITAL_OUT,
    _S.AI_CURRENT: _K.ANALOGUE_IN,
    _S.AI_VOLTAGE: _K.ANALOGUE_IN,
    _S.AO_CURRENT: _K.ANALOGUE_OUT,
    _S.AO_VOLTAGE: _K.ANALOGUE_OUT,
    _S.RTD: _K.ANALOGUE_IN,
    _S.RELAY: _K.DIGITAL_OUT,
}


def test_every_signal_type_has_a_row() -> None:
    """Each member of `SignalType` is a key of the table."""
    assert set(SIGNAL_TYPES) == set(SignalType)


def test_signal_kind_reproduces_the_old_mapping() -> None:
    """Each signal type gives the kind the hand-written table gave."""
    assert {signal: signal_kind(signal) for signal in SignalType} == _OLD


def test_a_missing_row_names_the_member() -> None:
    """`complete` on a table without `RTD` raises and names it."""
    short = {s: r for s, r in SIGNAL_TYPES.items() if s is not SignalType.RTD}
    with pytest.raises(RuntimeError, match="RTD"):
        complete(short, SignalType)


def test_rows_are_frozen() -> None:
    """A row refuses an assignment."""
    with pytest.raises(dataclasses.FrozenInstanceError):
        SIGNAL_TYPES[SignalType.DI].__setattr__("output", True)
