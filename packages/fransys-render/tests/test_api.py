import fransys_render


def test_public_names():
    assert sorted(fransys_render.__all__) == ["check", "pages"]
