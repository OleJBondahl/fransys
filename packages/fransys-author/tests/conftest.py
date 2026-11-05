"""The author tests' `parts` fixture; the catalogue builders are in `author_catalogue`."""

import pytest
from author_catalogue import build_test_catalogue

lazy from fransys_model.kernel import Draft


@pytest.fixture
def parts() -> Draft:
    """A fresh test catalogue `Draft` (`Design(parts)`)."""
    return build_test_catalogue()
