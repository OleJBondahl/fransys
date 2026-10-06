import fransys_parts


def test_public_names():
    assert sorted(fransys_parts.__all__) == [
        "PartLibraryError",
        "SUPPORTED_SCHEMAS",
        "lint",
        "load",
        "load_path",
    ]


def test_supported_schemas():
    """P4: schema 1 is the only accepted part-file schema version today."""
    assert frozenset({1}) == fransys_parts.SUPPORTED_SCHEMAS
