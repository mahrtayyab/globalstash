"""globalstash: thread-safe process-wide global state."""
from .core import GlobalState, g, get_state

__all__ = ["GlobalState", "g", "get_state"]
__version__ = "0.1.0"
