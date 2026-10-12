"""TradeGuard — offline trading-behaviour risk agent (zero dependencies)."""
from . import core

__version__ = "1.0.0"
__all__ = ["core", "analyze"]


def analyze(*args, **kwargs):
    """Convenience wrapper around core.analyze()."""
    return core.analyze(*args, **kwargs)
