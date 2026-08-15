# The single source of truth for the version. pyproject.toml reads __version__
# from this file via [tool.hatch.version], so it must stay a plain string literal.
__version__ = "3.0"

VERSIONSTR = __version__
VERSION = tuple(map(int, __version__.split(".")))
