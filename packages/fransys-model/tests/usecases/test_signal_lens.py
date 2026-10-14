"""`signal_lens` (model-0197): the cabinet's PLC modules, channels and field devices."""

from cabinet import build_cabinet

from fransys_model.derive import (
    SignalKind,
    plc_channel_rows,
    signal_lens,
)
from fransys_model.kernel import freeze


def test_the_lens_lists_every_channel_with_its_kind_and_field_device() -> None:
    """Channels and bound devices agree with the PLC list; every kind appears on this design."""
    model = freeze(build_cabinet())
    lens = signal_lens(model)
    channels = [c for module in lens for c in module.channels]
    rows = plc_channel_rows(model)
    assert len(channels) >= len(rows) > 0
    bound = [c for c in channels if c.device is not None]
    assert sorted(str(c.signal_name) for c in bound) == sorted(
        str(r.signal_name) for r in rows if r.field_device
    )
    assert all(c.device_item is not None and c.device_designation for c in bound)
    assert {c.kind for c in channels} <= set(SignalKind)
    assert len({c.kind for c in channels}) > 1


def test_the_lens_lists_no_module_without_a_channel() -> None:
    """Breaks if a PLC module with no channel is listed, as an empty table (O8)."""
    model = freeze(build_cabinet(cpu=True))
    lens = signal_lens(model)
    assert len(lens) == len(signal_lens(freeze(build_cabinet()))) == 3
    assert all(module.channels for module in lens)
