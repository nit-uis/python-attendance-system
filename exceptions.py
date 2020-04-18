class Error(Exception):
    """Base class for exceptions in this module."""
    pass


class ExceedError(Error):
    pass


class NotFoundError(Error):
    pass


class NotMatchedError(Error):
    pass


class MovieError(Error):
    pass
