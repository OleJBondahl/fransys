"""Board netlist check (spec E9): the relay board's KiCad netlist intermediate.

`fr.write`'s intermediates naming writes one `netlist-{ref}.net` per board, `ref` being the
board item's product designation with its group and tag (`PLC-U1-U2` in this design: the
board sits in the PLC function group of the system, tagged `U2` in the cabinet `U1`) -- look
for it under the fresh `intermediates` dir rather than hardcoding the exact tmp-path root.
"""

import re

EXPECTED_FOOTPRINTS_BY_REF = {
    "K1": "Relay_THT:Relay_SPDT_Finder_40.61",
    "K2": "Relay_THT:Relay_SPDT_Finder_40.61",
    "J1": "Connector_Phoenix_MSTB:PhoenixContact_MSTBA_2,5_3-G-5,08_1x03_P5.08mm_Horizontal",
    "J2": "Connector_Phoenix_MSTB:PhoenixContact_MSTBA_2,5_3-G-5,08_1x03_P5.08mm_Horizontal",
}


def test_board_netlist_is_named_for_the_full_ref(built: tuple) -> None:
    """The board's export file names carry its group, cabinet tag and own tag, not the bare ref."""
    _result, out_dir, intermediates = built
    assert (intermediates / "netlist-PLC-U1-U2.net").is_file()
    assert not (intermediates / "netlist-U2.net").exists()
    assert (out_dir / "all" / "EX-1-v1.2-connectors-PLC-U1-U2.csv").is_file()
    assert not (out_dir / "all" / "EX-1-v1.2-connectors-U2.csv").exists()


def test_board_netlist_has_four_components_with_footprints(built: tuple) -> None:
    _result, _out_dir, intermediates = built
    net_files = list(intermediates.glob("netlist-PLC-U1-U2.net"))
    assert len(net_files) == 1, f"expected exactly 1 board netlist file, found {net_files}"
    text = net_files[0].read_text(encoding="utf-8")

    refs = re.findall(r'\(comp \(ref "([^"]+)"\)', text)
    footprints = re.findall(r'\(footprint "([^"]*)"\)', text)
    assert len(refs) == 4, f"expected exactly 4 (comp ...) entries, got {len(refs)}: {refs}"
    assert len(footprints) == 4, f"expected exactly 4 footprints, got {len(footprints)}"

    by_ref = dict(zip(refs, footprints, strict=True))
    assert set(by_ref) == set(EXPECTED_FOOTPRINTS_BY_REF)
    for ref, footprint in by_ref.items():
        assert footprint, f"{ref} has an empty footprint"
        assert footprint == EXPECTED_FOOTPRINTS_BY_REF[ref]
