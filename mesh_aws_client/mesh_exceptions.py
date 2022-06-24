""" Exceptions for MESH client """


class BadRequestException(Exception):
    """
    Bad request error
    """

    def __init__(self, msg=None):
        super().__init__()
        self.msg = msg


class AuthenticationException(Exception):
    """
    Authentication failure
    """

    def __init__(self, msg=None):
        super().__init__()
        self.msg = msg
