import fransys_overview


def test_public_names():
    assert sorted(fransys_overview.__all__) == ["html"]
