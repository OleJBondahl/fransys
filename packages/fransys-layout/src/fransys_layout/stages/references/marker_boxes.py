"""LD3 (c), D4, S4: the size of a reference's box and of a pure off stub's, decided with its text.

A size is a decision (S9); where the box stands is `texts`' (`texts.markers`), which stands it
at its port through the text placer's one anchoring rule.
"""

from typing import TYPE_CHECKING

from fransys_layout.geometry import Facing, text_width
from fransys_model.derive.drawing_text import position_text, row_letter

from .digits import FLOOR, Digits

if TYPE_CHECKING:
    from fransys_layout.stages.types import Profile, SheetFormat


def reference_texts(sheet: SheetFormat, digits: Digits) -> tuple[str, ...]:
    """The widest `#n-<position>` of each form derive's `position_text` prints at `digits`."""
    column, row = sheet.frame_columns, row_letter(sheet.frame_rows - 1)
    page = int("9" * digits.sheets)
    forms = [position_text(page, column, row, (), own_page=1)]
    if digits.other_sets:
        other = int("9" * digits.other_sets)
        forms.append(position_text(page, column, row, (), other))
        forms.append(position_text(page, column, row, digits.prefix, other))
    return tuple(f"#{'9' * digits.refs}-{form}" for form in forms)


def reference_box_width(sheet: SheetFormat, profile: Profile, *, digits: Digits = FLOOR) -> int:
    """LD3 (c), S4: the fixed reference/star box width, one per drawing set and sheet format."""
    widest = max(
        text_width(text, height=profile.text_height) for text in reference_texts(sheet, digits)
    )
    return widest + (2 * profile.marker_padding)


def reference_size(
    sheet: SheetFormat,
    profile: Profile,
    *,
    lines: int = 1,
    digits: Digits = FLOOR,
) -> tuple[int, int]:
    """LD3 (c): a reference's `(width, height)`, `lines` lines tall at its set's fixed width."""
    height = lines * profile.text_height + 2 * profile.marker_padding
    return reference_box_width(sheet, profile, digits=digits), height


def stub_size(text: str, profile: Profile) -> tuple[int, int]:
    """A pure off stub's `(width, height)`: its text measured, one line (D4, not LD3's width)."""
    padding = profile.marker_padding
    height = profile.text_height + 2 * padding
    return text_width(text, height=profile.text_height) + 2 * padding, height


def reads_along(run: int | None, facing: Facing) -> bool:
    """S20 M1: a stub's text reads along its wire, turned, at an N or S port and in no C21 run."""
    return run is None and facing in (Facing.N, Facing.S)
