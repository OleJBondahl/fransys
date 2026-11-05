"""The bundle forms the placement reads (R736)."""

#: The forms beyond the poles of a device that draw as trunks: empty until CABLE-TRUNK-ON (KI-171).
TRUNK_FORMS: frozenset[str] = frozenset[str]()

#: The forms `derive.bundle_of` answers for the placement: a device's poles and the trunk forms.
DRAWN_FORMS = frozenset({"pole", *TRUNK_FORMS})
