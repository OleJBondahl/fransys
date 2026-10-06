"""The cover/notes Markdown subset: parsing, escaping and Typst emission (spec P6)."""

from fransys_pdf._markdown import (
    BulletList,
    Heading,
    NumberedList,
    Paragraph,
    Run,
    Unsupported,
    parse,
    to_typst,
    unsupported,
)


def test_heading_levels_one_to_three():
    assert parse("# A\n\n## B\n\n### C") == (
        Heading(1, 1, (Run("plain", "A"),)),
        Heading(3, 2, (Run("plain", "B"),)),
        Heading(5, 3, (Run("plain", "C"),)),
    )


def test_paragraph_lines_join_with_a_space():
    assert parse("line one\nline two") == (Paragraph(1, (Run("plain", "line one line two"),)),)


def test_blank_line_separates_paragraphs():
    assert parse("first\n\nsecond") == (
        Paragraph(1, (Run("plain", "first"),)),
        Paragraph(3, (Run("plain", "second"),)),
    )


def test_bold_and_italic_runs():
    assert parse("plain **bold** plain *italic* plain") == (
        Paragraph(
            1,
            (
                Run("plain", "plain "),
                Run("bold", "bold"),
                Run("plain", " plain "),
                Run("italic", "italic"),
                Run("plain", " plain"),
            ),
        ),
    )


def test_spaced_asterisks_stay_literal_but_closed_ones_still_open_emphasis():
    """Spec P6 amendment: emphasis opens only before a non-space and closes only after one
    (CommonMark's flanking rule, reduced to this subset). The spec names this exact contrast.
    """
    assert parse("a * b * c") == (Paragraph(1, (Run("plain", "a * b * c"),)),)
    assert parse("a *b* c") == (
        Paragraph(1, (Run("plain", "a "), Run("italic", "b"), Run("plain", " c"))),
    )


def test_arithmetic_with_spaced_asterisks_stays_literal():
    assert parse("torque * 1.5 * factor") == (
        Paragraph(1, (Run("plain", "torque * 1.5 * factor"),)),
    )


def test_bullet_list():
    assert parse("- one\n- two") == (
        BulletList(1, ((Run("plain", "one"),), (Run("plain", "two"),))),
    )


def test_numbered_list_any_number():
    assert parse("1. first\n7. second") == (
        NumberedList(1, ((Run("plain", "first"),), (Run("plain", "second"),))),
    )


def test_markup_injection_is_never_interpreted():
    """The spec's own named case: `#let x = 1` and `*not emphasis` reach Typst as text."""
    elements = parse("#let x = 1\n\n*not emphasis")
    assert elements == (
        Paragraph(1, (Run("plain", "#let x = 1"),)),
        Paragraph(3, (Run("plain", "*not emphasis"),)),
    )
    source = to_typst(elements)
    assert '"#let x = 1"' in source
    assert '"*not emphasis"' in source
    assert "#let" not in source.replace('"#let x = 1"', "")


def test_unsupported_constructs_report_line_and_construct():
    text = (
        "#### too deep\n\n"
        "| a | b |\n\n"
        "![alt](x.png)\n\n"
        "[link](x)\n\n"
        "`code`\n\n"
        "```\n\n"
        "> quoted\n\n"
        "  - indented\n\n"
        "<div>html</div>"
    )
    found = unsupported(parse(text))
    assert [(u.line, u.construct) for u in found] == [
        (1, "heading level 4"),
        (3, "table"),
        (5, "image"),
        (7, "link"),
        (9, "inline code"),
        (11, "code fence"),
        (13, "block quote"),
        (15, "indented list"),
        (17, "raw HTML"),
    ]


def test_unsupported_line_is_printed_verbatim_as_its_own_paragraph():
    elements = parse("before\n\n`code`\n\nafter")
    assert elements == (
        Paragraph(1, (Run("plain", "before"),)),
        Unsupported(3, "inline code", "`code`"),
        Paragraph(5, (Run("plain", "after"),)),
    )
    source = to_typst(elements)
    assert '"`code`"' in source


def test_escaping_backslash_and_quote_in_a_text_literal():
    elements = parse('a "quote" and a \\backslash')
    source = to_typst(elements)
    assert '\\"quote\\"' in source
    assert "\\\\backslash" in source
