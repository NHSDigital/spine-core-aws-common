"""Common methods and classes used for mesh client"""


class SingletonCheckFailure(Exception):
    """Singleton check failed"""

    def __init__(self, msg=None):
        super().__init__()
        if msg:
            self.msg = msg


class MeshCommon:  # pylint: disable=too-few-public-methods
    """Common"""

    MIB = 1024 * 1024 * 1024
    DEFAULT_CHUNK_SIZE = 20 * MIB
