"""Field case: `d.series` is given two bare pins, which carry no supply, rail or pole count to
set the wire width.

The bug: the `AuthorError` says "name a supply, a rail or a function with poles" and does not
say that a pin pair with an explicit wire is `d.detail.wire(a, b, wire=...)`.

Fixed by layout-0322: the message names `d.detail.wire`.
"""

import fransys as fr
import pytest
from fransys_author.errors import AuthorError


def test_the_error_names_the_detail_wire_spelling() -> None:
    d = fr.design("demo_parts")
    j1 = d.device("J1", "DEMO-CONN-2P")
    h1 = d.device("H1", "DEMO-LAMP-24")
    with pytest.raises(AuthorError, match=r"d\.detail\.wire"):
        d.series(j1["1"], h1["1"])
