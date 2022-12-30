class ApiError(Exception):
    "Raised when Api doesn't work"
    pass


class UnknownStatus(Exception):
    "Raised when the status value is unknown"
    pass
