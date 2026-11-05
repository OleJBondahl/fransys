"""A refusal that lists a part's names lists them in natural order: `m2` before `m10`."""

import fransys_parts
import pytest
from fransys_author import AuthorError
from fransys_author.design import Design

_LIBRARY = 'schema = 2\nname = "l"\nversion = "0.1.0"\ndescription = "d"\n'
_PART = 'schema = 2\n\n[part]\nmpn = "NS-1"\nmanufacturer = "Demo"\ndescription = "d"\ncategory = "generic"\nclass_code = "X"\n' + "".join(
    f'\n[[function]]\nname = "{name}"\nkind = "generic"\nports = [{{ name = "{name}", role = "generic" }}]\n' for name in ("m10", "m2")
)


def test_a_missing_function_lists_the_part_functions_in_natural_order(tmp_path):
    root = tmp_path / "lib"
    (root / "parts").mkdir(parents=True)
    (root / "library.toml").write_text(_LIBRARY)
    (root / "parts" / "ns1.toml").write_text(_PART)
    s = Design(fransys_parts.load_path(root))
    with pytest.raises(AuthorError, match=r"it has: m2, m10$"):
        s.operating("NS-1", "nope")
