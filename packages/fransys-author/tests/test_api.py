import fransys_author


def test_public_names_match_the_spec():
    assert set(fransys_author.__all__) == {
        "AuthorError",
        "Cable",
        "Design",
        "Fn",
        "Group",
        "Item",
        "Location",
        "Operating",
        "Port",
        "Rating",
        "Scope",
        "Strip",
        "Terminal",
        "Wiring",
    }
