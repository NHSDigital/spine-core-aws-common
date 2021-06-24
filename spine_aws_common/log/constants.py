"""
Created 18th June 2019
"""


class LoggingConstants:
    # pylint:disable=too-few-public-methods
    """
    Logging Constants
    """

    SECTION_LEVEL = "Log Level"
    SECTION_TEXT = "Log Text"

    LFR_OPERATIONS = "operations"
    LFR_AUDIT = "audit"
    LFR_CRASHDUMP = "crashdump"
    LFR_CONSOLE = "console"
    LFR_NMS = "monitor"

    LOGGING_DIRECTORIES = [LFR_AUDIT, LFR_OPERATIONS, LFR_CRASHDUMP, LFR_NMS]

    TRACE = 8
    DEBUG = 7
    INFO = 6
    WARN = 4
    ERROR = 3
    CRITICAL = 1
    AUDIT = 0

    LR_CRASHDUMP = "UTI9992"
    LOG_SUFFIX = ".log"

    IDENTIFIERS = ["internalID", "sessionid"]

    SPINE_LOGGER = "spine"
