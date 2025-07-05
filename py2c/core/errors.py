class ErrorUsage(Exception):
    """This exception is raised when the user uses the program incorrectly."""
    pass

class UserError(Exception):
    """This exception is raised when the user's code has an error."""
    pass

class ParserError(Exception):
    """A base class error for main processor. This exception is raised when the parser encounters an error."""
    pass

class VisitorError(Exception):
    """A base class error for the visitor. This exception is raised when the visitor encounters an error."""
    pass

class LinterError(Exception):
    """A base class error for the linter. This exception is raised when the linter encounters an error."""
    pass
