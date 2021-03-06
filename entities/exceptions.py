class Error(Exception):
    """Base class for exceptions in this module."""
    pass


class CacheError(Error):
    pass


class MemberError(Error):
    pass


class MemberGroupError(Error):
    pass


class EventError(Error):
    pass


class Unauthorized(Error):
    pass