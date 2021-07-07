"""
Created 18th June 2019
"""
import logging

from spine_aws_common.log.logutil import write_log
from spine_aws_common.log.masking import mask_pid


SEVERITY_INPUT_MAP = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARN": logging.WARN,
    "INFO": logging.INFO,
    # Allow us to enable python debug independently
    "DEBUG": logging.INFO,
    # Allow us to enable python debug independently
    "TRACE": logging.DEBUG,
}


class LoggingAdapter(logging.Handler):
    """
    Adapter to allow libraries that use python logging to output to our logger
    """

    CRITICAL = "UTI9998"
    ERROR = "UTI9997"
    WARN = "UTI9996"
    INFO = "UTI9995"
    DEBUG = "UTI9994"
    TRACE = "UTI9993"

    _EXCLUSIVE_USE_CHANNEL_FINDER = "in exclusive use"
    _EXCLUSIVE_USE_CHANNEL_OUTPUT = "Connection blocked due to exclusive use"

    _EXCLUSIVE_USE_CALLBACK_FINDER = "bound method BlockingChannel._on_channel_closed"
    _EXCLUSIVE_USE_CALLBACK_OUTPUT = "Callback terminated due to exclusive use"

    # Convert tuples to improve message or adjust criticality
    # E.g.
    # 'pika.connection' reports CRITICAL 'Attempted to send frame when closed'
    # - this is not CRITICAL - SPII-13851

    # Use to replace log message when substring found
    _MESSAGE_MAP = {
        _EXCLUSIVE_USE_CHANNEL_FINDER: _EXCLUSIVE_USE_CHANNEL_OUTPUT,
        _EXCLUSIVE_USE_CALLBACK_FINDER: _EXCLUSIVE_USE_CALLBACK_OUTPUT,
    }

    # Use for mapping logs with a specific message
    _LOGGER_DETAIL_MAP = {
        (
            "pika.connection",
            logging.CRITICAL,
            "CRITICAL",
            "Attempted to send frame when closed",
        ): (
            "pika.connection",
            logging.ERROR,
            "ERROR",
            "Attempted to send frame when closed",
        ),
        ("pika.channel", logging.WARNING, "WARNING", _EXCLUSIVE_USE_CHANNEL_OUTPUT): (
            "pika.channel",
            logging.INFO,
            "INFO",
            _EXCLUSIVE_USE_CHANNEL_OUTPUT,
        ),
        ("pika.callback", logging.ERROR, "ERROR", _EXCLUSIVE_USE_CALLBACK_OUTPUT): (
            "pika.callback",
            logging.INFO,
            "INFO",
            _EXCLUSIVE_USE_CALLBACK_OUTPUT,
        ),
        (
            "pika.adapters.base_connection",
            logging.CRITICAL,
            "CRITICAL",
            "Tried to handle an error where no error existed",
        ): (
            "pika.adapters.base_connection",
            logging.WARN,
            "WARN",
            "Tried to handle an error where no error existed",
        ),
    }

    # Use for mapping of all logs of a given name
    _LOGGER_SUMMARY_MAP = {
        ("tornado.access", logging.INFO, "INFO"): (
            "tornado.access",
            logging.DEBUG,
            "DEBUG",
        )
    }

    def __init__(self, log_object=None):
        logging.Handler.__init__(self, logging.DEBUG)
        self.log_object = log_object

    def emit(self, record):
        """Override emit to output to our log file"""
        name, level, levelname, message = self._switch_log(
            record.name, record.levelno, record.levelname, record.getMessage()
        )

        masked_message = mask_pid(message)
        log_reference = self._get_log_reference(level)
        log_dict = {"logger": name, "message": masked_message, "level": levelname}

        # Note that we don't log sys.exc_info() here since there is no
        # guarantee that a third party library is logging in response to an
        # exception. This has lead to misleading stack traces being output
        # that were nothing to do with the logged message.
        if self.log_object:
            self.log_object.write_log(log_reference, None, log_dict)
        else:
            # Needs to be improved.
            if "logReference=" in message:
                return
            write_log(log_reference, None, log_dict)

    def _switch_log(self, name, level, levelname, message):
        """
        If the log is in the dictionary, return the dictionary output instead
        """
        name, level, levelname = LoggingAdapter._LOGGER_SUMMARY_MAP.get(
            (name, level, levelname), (name, level, levelname)
        )

        for finder, value in self._MESSAGE_MAP.items():
            if finder in message:
                message = value

        return LoggingAdapter._LOGGER_DETAIL_MAP.get(
            (name, level, levelname, message), (name, level, levelname, message)
        )

    def _get_log_reference(self, level):
        """
        Get the log reference based on the output map
        """
        output_map = {
            logging.CRITICAL: self.CRITICAL,
            logging.FATAL: self.CRITICAL,
            logging.ERROR: self.ERROR,
            logging.WARNING: self.WARN,
            logging.WARN: self.WARN,
            logging.INFO: self.INFO,
            # Allow us to enable python debug independently
            logging.DEBUG: self.TRACE,
        }

        return output_map[level]


def configure_third_party_logging_adapter(severity_threshold):
    """
    Configure an adapter to allow libraries that use standard Python logging to
    output to our log files.
    """
    root_logger = logging.getLogger()
    if root_logger.handlers:
        for handler in root_logger.handlers:
            root_logger.removeHandler(handler)
    root_logger.setLevel(SEVERITY_INPUT_MAP[severity_threshold])

    adapter = LoggingAdapter()
    root_logger.addHandler(adapter)
