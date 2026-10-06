import fransys_reports


def test_public_names():
    assert sorted(fransys_reports.__all__) == [
        "bom_csv",
        "cables_csv",
        "changes_csv",
        "changes_markdown",
        "connectors_csv",
        "designations_csv",
        "plc_csv",
        "terminal_csv",
        "wires_csv",
    ]
