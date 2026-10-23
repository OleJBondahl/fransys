"""`DESIGNATION_SCHEME`: the signs and the class-code letter rules of an IEC 81346 designation (M3).

One table the model's grammar, the author's tag rules and the parts lint read. Each value is
copied from the site named on it (EL-9 part B); no reader types a sign or a letter set again.
"""

from dataclasses import dataclass
lazy from collections.abc import Iterable

from .enums import Aspect
from .roles_types import complete


@dataclass(frozen=True, slots=True)
class DesignationScheme:
    """The sign of each aspect, the aspects a reference prints, and the class-code letter rules.

    `reference_aspects` is the order a reference prints its aspect segments (`=` then `+`, before
    the product part). `class_code` is a regular expression for the whole code.
    """

    signs: frozendict[Aspect, str]
    reference_aspects: tuple[Aspect, ...]
    class_code: str
    forbidden_letters: frozenset[str]
    reserved_letters: frozenset[str]

    def sign(self, aspect: Aspect) -> str:
        """The sign that opens a segment of `aspect`: `=` function, `-` product, `+` location."""
        return self.signs[aspect]

    def signed(self, aspect: Aspect, text: str) -> str:
        """`text` behind `aspect`'s sign: `-K1` for the product aspect."""
        return self.signs[aspect] + text

    def join(self, segments: Iterable[tuple[str, str]], *, bare: bool = False) -> str:
        """The one join: each (sign, label) written out; `bare` leaves the first sign off."""
        pairs = list(segments)
        text = "".join(sign + label for sign, label in pairs)
        return text[len(pairs[0][0]) :] if bare and pairs else text

    def letter_rule(self, code: str) -> str | None:
        """Return "forbidden" or "reserved" when `code` breaks the IEC letter rule, else `None`."""
        if code[0] in self.forbidden_letters:
            return "forbidden"
        return "reserved" if code[0] in self.reserved_letters else None

    def sign_characters(self) -> str:
        """Every sign, joined: what a bare tag must not start with."""
        return "".join(self.signs.values())


DESIGNATION_SCHEME = DesignationScheme(
    # unit_nodes.py:26 SIGNS (function, location); author surface/_tags.py:6 _PREFIX (product)
    signs=frozendict(
        complete({Aspect.FUNCTION: "=", Aspect.PRODUCT: "-", Aspect.LOCATION: "+"}, Aspect)
    ),
    reference_aspects=(Aspect.FUNCTION, Aspect.LOCATION),
    # parts/lint.py:36 _CLASS_CODE; author surface/_unit_tags.py:9 (same set of strings)
    class_code=r"[A-Z]{1,3}",
    # parts/lint.py:39, IEC 81346-2:2019: A, I and O shall not be a class code
    forbidden_letters=frozenset({"A", "I", "O"}),
    # parts/lint.py:42, IEC 81346-2:2019 reserves D, L, V, Y, Z; J is the owner's override
    reserved_letters=frozenset({"D", "L", "V", "Y", "Z"}),
)
