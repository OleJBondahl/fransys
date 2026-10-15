"""Acceptance tests for `kernel.record`."""

from fransys_kernel import AuthoringKey, Id, Value, field_specs, record, value


def test_field_specs_lists_reference_fields_with_target_kind() -> None:
    """`Id[K]`, `Id[K] | None` and `tuple[Id[K], ...]` are recognised as references.

    A plain field has `ref_kind is None`.
    """

    @record(kind="referenced_probe")
    class Referenced:
        id: Id[Referenced]
        key: AuthoringKey
        ext: frozendict[str, Value] = frozendict()

    @value
    class Refs:
        plain: str
        single: Id[Referenced]
        optional: Id[Referenced] | None
        many: tuple[Id[Referenced], ...]

    specs = {spec.name: spec for spec in field_specs(Refs)}
    assert specs["plain"].ref_kind is None
    assert specs["single"].ref_kind == "referenced_probe"
    assert specs["optional"].ref_kind == "referenced_probe"
    assert specs["many"].ref_kind == "referenced_probe"
