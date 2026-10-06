"""WAGO export check (spec E9): `wago-U1.xml` lists 4 DI and 4 DO channels.

Names read from the currently-committed `out/cabinet/wago-U1.xml` before writing
this test, per the brief: `Name=` is `{field_device}_{signal_name}` for a wired DI channel
(`B12_P1_OVERLOAD`, `Q11_P1_RUNNING`, ...), `{field_device_with_underscore}_{signal_name}` for
a wired DO channel (`U2_K1_P1_RUN`, `U2_K2_P2_RUN`), and `{module}_{Nr}` (WAGO's own zero-based
channel number, not the one-based `plc.csv` channel index) for a spare DO channel: `DO1_2` and
`DO1_3` are WAGO `Nr` 2 and 3, i.e. `plc.csv`'s `DO1:3` and `DO1:4` -- see the STEP 4 report
for this off-by-one between the two exports. The DI field device is the overload contact
(`-Bn2`) or the contactor aux contact (`-Qn1`), not the DI channel itself (reviewfix PART 1).
"""

import xml.etree.ElementTree as ET
from pathlib import Path

EXPECTED_DI_CHANNEL_NAMES = [
    "B12_P1_OVERLOAD",
    "Q11_P1_RUNNING",
    "B22_P2_OVERLOAD",
    "Q21_P2_RUNNING",
]
EXPECTED_DO_CHANNEL_NAMES = ["U2_K1_P1_RUN", "U2_K2_P2_RUN", "DO1_2", "DO1_3"]


def test_wago_export_lists_di_and_do_modules_and_channels(built: tuple) -> None:
    _result, out_dir, _intermediates = built
    xml_path: Path = out_dir / "cabinet" / "pump-cabinet-v1.6-wago-U1.xml"
    root = ET.parse(xml_path).getroot()

    modules = root.findall("Module")
    assert len(modules) == 2, f"expected exactly 2 <Module> elements, got {len(modules)}"

    di_modules = [m for m in modules if "DI" in m.get("Name", "")]
    do_modules = [m for m in modules if "DO" in m.get("Name", "")]
    assert len(di_modules) == 1, f"expected exactly 1 DI module, got {len(di_modules)}"
    assert len(do_modules) == 1, f"expected exactly 1 DO module, got {len(do_modules)}"

    di_channels = di_modules[0].findall("Channel")
    assert len(di_channels) == 4, f"expected exactly 4 DI channels, got {len(di_channels)}"
    di_names = [c.get("Name") for c in di_channels]
    assert di_names == EXPECTED_DI_CHANNEL_NAMES

    do_channels = do_modules[0].findall("Channel")
    assert len(do_channels) == 4, f"expected exactly 4 DO channels, got {len(do_channels)}"
    do_names = [c.get("Name") for c in do_channels]
    assert do_names == EXPECTED_DO_CHANNEL_NAMES
