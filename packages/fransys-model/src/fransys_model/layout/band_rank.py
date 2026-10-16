"""The one reader of `Profile.band_ranks`: the rank of a band key (EL-2a, M8)."""

lazy from .formats import Profile


def band_rank(profile: Profile, band: str | None) -> int | None:
    """The rank `profile` gives the band key `band`; `None` for no band or an unranked key.

    Example: with the house profile, `band_rank(profile, "coil")` is 4 and
    `band_rank(profile, "bar")` is `None`.
    """
    return None if band is None else profile.band_ranks.get(band)
