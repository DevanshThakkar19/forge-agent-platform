"""Forge API package."""

from importlib.metadata import PackageNotFoundError, version

__version__ = "0.1.0"


def package_version() -> str:
    """Return the installed distribution version, or the source fallback."""
    try:
        return version("forge-agent-platform")
    except PackageNotFoundError:
        return __version__
