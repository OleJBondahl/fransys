"""The installed version of the fransys distribution, read once."""

import importlib.metadata

__version__ = importlib.metadata.version("fransys")
