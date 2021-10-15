"""
Created 18th June 2018
"""
import configparser
import logging
import time

from spine_aws_common.log.constants import LoggingConstants

# Python Logging values commented out for reference.
AUDIT = 53
CRASH = 52
MONITOR = 51
# CRITICAL = 50
# FATAL = CRITICAL
# ERROR = 40
WARN = 31
# WARNING = 30
# WARN = WARNING
# INFO = 20
# DEBUG = 10
TRACE = 9
# NOTSET = 0

_LOG_BASE_CACHE = {}


def get_log_base_config(log_base):
    """
    Read the log base config
    - all the config is now read in at startup to move from a configparser
      object to a dictionary of tuples.
    This has a lower memory footprint (the difference in memory footprint
    is relevant to local builds - see SPII-18501)
    """
    if not log_base:
        return None

    # Use of str is required to support the case where a list of
    # log base config files have been provided
    log_base_dict = _LOG_BASE_CACHE.get(str(log_base))
    if not log_base_dict:
        log_base_config = configparser.RawConfigParser()
        log_base_config.read(log_base)
        log_base_dict = {}
        for log_ref in log_base_config.sections():
            try:
                level = log_base_config.get(log_ref, LoggingConstants.SECTION_LEVEL)
            except configparser.NoOptionError:
                level = "INFO"

            try:
                text = log_base_config.get(log_ref, LoggingConstants.SECTION_TEXT)
            except configparser.NoOptionError:
                text = log_base_config.get("UTI9999", "Log Text")

            log_base_dict[log_ref] = [level, text]

        _LOG_BASE_CACHE[str(log_base)] = log_base_dict

    return log_base_dict


class AuditFilter(logging.Filter):
    # pylint:disable=too-few-public-methods
    """
    Audit Directory Filter
    """

    def filter(self, record):
        """Only allow audit"""
        return record.levelno == AUDIT


class MonitorFilter(logging.Filter):
    # pylint:disable=too-few-public-methods
    """
    Monitor Directory Filter
    """

    def filter(self, record):
        """Only allow monitor"""
        return record.levelno == MONITOR


class CrashFilter(logging.Filter):
    # pylint:disable=too-few-public-methods
    """
    Crashdump Directory Filter
    """

    def filter(self, record):
        """Only allow crash"""
        return record.levelno == CRASH


class OperationsFilter(logging.Filter):
    # pylint:disable=too-few-public-methods
    """
    Operations Directory Filter
    """

    def filter(self, record):
        """Only allow critical and less"""
        return record.levelno <= logging.CRITICAL


class SpineLogFormatter(logging.Formatter):
    """
    Spine Log Formatter
    """

    def format_time(self, record, datefmt=None):
        """Format time"""
        converted_time = self.converter(record.created)
        time_str = time.strftime(datefmt, converted_time)
        return f"{time_str}.{int(record.msecs):0>3d}"


class SpineLogger(logging.Logger):
    """
    Spine Logger
    """

    def __init__(self, name):
        logging.Logger.__init__(self, name)

        self.log_root = None
        self.log_base = None
        self.process_name = None
        self.log_permission = None
        self.severity_threshold = None

        self.log_base_cache = {}
        self.log_base_dict = None

    def audit(self, msg, *args, **kwargs):
        """
        Log 'msg % args' with severity 'AUDIT'.
        """
        if self.isEnabledFor(AUDIT):
            self._log(AUDIT, msg, args, **kwargs)

    def monitor(self, msg, *args, **kwargs):
        """
        Log 'msg % args' with severity 'MONITOR'.
        """
        if self.isEnabledFor(MONITOR):
            self._log(MONITOR, msg, args, **kwargs)

    def crash(self, msg, *args, **kwargs):
        """
        Log 'msg % args' with severity 'CRASH'.
        """
        if self.isEnabledFor(CRASH):
            self._log(CRASH, msg, args, exc_info=True, **kwargs)

    @classmethod
    def get_process_name(cls):
        """Return the current log permission"""
        return logging.getLogger(LoggingConstants.SPINE_LOGGER).process_name

    @classmethod
    def get_log_permission(cls):
        """Return the current log permission"""
        return logging.getLogger(LoggingConstants.SPINE_LOGGER).log_permission

    @classmethod
    def get_log_base_dict(cls):
        """Return the current log base dict"""
        return logging.getLogger(LoggingConstants.SPINE_LOGGER).log_base_dict

    @classmethod
    def get_log_base_cache(cls):
        """Return the current log base cache"""
        return logging.getLogger(LoggingConstants.SPINE_LOGGER).log_base_cache

    @classmethod
    def get_severity_threshold(cls):
        """Return the current severity threshold"""
        return logging.getLogger(LoggingConstants.SPINE_LOGGER).severity_threshold


def clean_spine_logging():
    """
    Clean up the Spine Logging - setting the loggers back to how they were at
    the start. Used mainly for ensuring tests are tidied up nicely at the end.
    """
    root_logger = logging.getLogger()
    logging.root = root_logger
    logging.Logger.root = logging.root
    logging.Logger.manager = logging.Manager(logging.root)
