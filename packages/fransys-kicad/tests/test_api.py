import fransys_kicad


def test_public_names():
    assert sorted(fransys_kicad.__all__) == [
        "FINDING_CODES",
        "check",
        "netlist",
        "part_file_skeleton",
    ]
