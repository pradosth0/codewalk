"""codewalk: agent-authored, debugger-style visual walkthroughs of Python codebases."""

from .display import image
from .errors import CodewalkError, SpecError
from .spec import Walkthrough, load_walkthrough

__version__ = "0.1.0"
__all__ = ["Walkthrough", "load_walkthrough", "image", "CodewalkError", "SpecError", "__version__"]
