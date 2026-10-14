"""`fr.__version__` is the installed distribution's version, and not a public name."""

import importlib.metadata

import fransys as fr


def test_version_is_the_installed_distribution_version():
    assert fr.__version__ == importlib.metadata.version("fransys")


def test_version_is_a_dunder_not_in_all():
    assert "__version__" not in fr.__all__
