"""More layout codes a consumer acts on (BUILD-MESSAGES M1)."""

from fransys_model.kernel import CodeInfo, Severity

FINDING_CODES: tuple[CodeInfo, ...] = (
    CodeInfo(
        code="SHEET_FORMAT_UNUSED",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause=(
            "An authored sheet format is named by no layout profile, so pages use the house "
            "sheet (or the profile's format)."
        ),
        fix=(
            "Name it in the settings file's [paper] table, or remove it. "
            'Write: [paper] default = "A2" in the settings file, '
            "passed as fr.build(settings=fr.settings(path))."
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="TEXT_TOO_SMALL",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause=(
            "A layout profile's `text_height_mm` is under its `min_text_height_mm`. Once per "
            "profile; nothing is shrunk or grown."
        ),
        fix=(
            "Raise `text_height_mm`, or lower `min_text_height_mm` if the small text is "
            "intended. Write: d.layout.profile(text_height_mm=...)."
        ),
        page="findings-render",
    ),
)
