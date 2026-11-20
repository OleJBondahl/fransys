"""The root fixture build a laid-out model (WP order Part C1)."""

import pytest


@pytest.mark.parametrize("fixture", ["demo_cabinet"])
def test_demo_fixture_builds_a_laid_out_model(fixture, request):
    built = request.getfixturevalue(fixture)
    assert built.digests["core"]
    assert built.digests["facet"]
    assert built.digests["layout"]


# INK_WITHOUT_CONDUCTOR: a falling stock of this file's builds on KI-974 (docs/KNOWN-ISSUES.toml, el-0130).
