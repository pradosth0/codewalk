"""Exception types."""


class CodewalkError(Exception):
    """Base class for codewalk errors."""


class SpecError(CodewalkError):
    """An invalid walkthrough definition (bad field, unknown file, unparsable expression)."""
