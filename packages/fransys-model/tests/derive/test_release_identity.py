"""`release_identity` (model-0280): a unit's own release, or the project's for `unit=None`."""

from plant import Plant

from fransys_model.derive import export_prefix, export_set_name, release_identity
from fransys_model.kernel import make_id
from fransys_model.vocab.project import Project


def _project() -> Project:
    key = ("examples", "project", "p")
    return Project(
        id=make_id(Project, key),
        key=key,
        title="Invented",
        number="P-0001",
        customer="Invented AS",
        revision=3,
        author="N. N.",
        version=2,
    )


def test_a_unit_reads_its_release_and_a_nested_unit_its_own() -> None:
    plant = Plant()
    outer = plant.unit("outer", name="outer-u", version=2, revision=4, interface="7")
    inner = plant.unit("inner", name="inner-u", parent=outer, revision=9, interface="3")
    model = plant.model()
    got = release_identity(model, outer)
    assert (got.name, got.version, got.revision, got.interface) == ("outer-u", 2, 4, "7")
    got = release_identity(model, inner)
    assert (got.name, got.version, got.revision, got.interface) == ("inner-u", 1, 9, "3")


def test_the_system_reads_the_project_with_an_empty_interface() -> None:
    plant = Plant()
    plant.add(_project())
    got = release_identity(plant.model(), None)
    assert (got.name, got.version, got.revision, got.interface) == ("P-0001", 2, 3, "")


def test_export_names_follow_the_identity_and_a_model_without_a_project_has_none() -> None:
    with_project = Plant()
    with_project.add(_project())
    unit = with_project.unit("u", name="u-rel", version=2, revision=5)
    model = with_project.model()
    assert export_set_name(model, None) == "P-0001"
    assert export_prefix(model, None) == "P-0001-v2.3"
    assert export_prefix(model, unit) == "u-rel-v2.5"
    bare = Plant().model()
    assert export_set_name(bare, None) == ""
    assert export_prefix(bare, None) == ""
