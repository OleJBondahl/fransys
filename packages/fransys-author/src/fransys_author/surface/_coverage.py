"""Surface mixin for EA-COVERAGE: every other spelling of today's author API (EA11).

It joins the mixins of `_links`, `_facts` and `_layout`; `Design` lists it among its bases.
"""

from ._facts import Facts
from ._layout import Layouts
from ._links import Links


class Coverage(Links, Facts, Layouts):
    """The calls of the three mixins it joins."""
