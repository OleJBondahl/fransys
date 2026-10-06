import fransys_wago


def test_public_names():
    assert sorted(fransys_wago.__all__) == ["modules_xml"]
