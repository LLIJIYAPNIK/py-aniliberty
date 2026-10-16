"""Installed package version (not public API — use ``aniliberty.__version__``).

Lives in its own module so that ``_http.py`` can put the version into the ``User-Agent``
header without importing the package's ``__init__`` (which imports ``_http.py`` itself).
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("py-aniliberty")
except PackageNotFoundError:  # pragma: no cover - only when running from a raw source tree
    __version__ = "0.0.0"
