# Minimal package init; exposes a version and a tiny function for tests
__all__ = ["__version__", "echo"]
__version__ = "0.1.0"

from .core import echo  # re-export
