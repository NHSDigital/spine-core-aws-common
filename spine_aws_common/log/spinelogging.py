"""
Created 18th June 2018
"""
from copy import deepcopy
from logging import Formatter, LoggerAdapter, LogRecord, StreamHandler
from typing import List, Tuple
import configparser
import logging
import os
import sys

from spine_aws_common.log.constants import LoggingConstants
from spine_aws_common.log.details import LogDetails, get_log_details
from spine_aws_common.log.formatting import (
    add_default_keys,
    create_log_line,
    evaluate_log_keys,
)
from spine_aws_common.log.masking import mask_url

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

# See https://docs.python.org/3/library/logging.html#logging.Logger.debug
PYTHON_INSPECTED_ARGS = ["exc_info", "extra", "stack_info", "stacklevel"]

# Log_Level, Process and logReference are mandatory and processed by the adapter
SPINE_SPLUNK_LOG_FORMAT = (
    "{asctime}.{msecs:03.0f} - "
    "Log_Level={level_name} Process={process_name} logReference={log_reference} - "
    "{message}"
)
SPINE_SPLUNK_DATEFORMAT = "%d/%m/%Y %H:%M:%S"


class LambdaFormatter(Formatter):
    """Lambda creates new cloudwatch entries for every newline separated log line"""

    def format(self, record: LogRecord) -> str:
        fmted = super().format(record)
        if not record.exc_info:
            return fmted
        return "\r".join(fmted.split("\n")) + "\n"


def get_spine_splunk_formatter() -> Formatter:
    """Get a pre-baked Spine-style Splunk log formatter"""
    formatter = LambdaFormatter(
        SPINE_SPLUNK_LOG_FORMAT,
        datefmt=SPINE_SPLUNK_DATEFORMAT,
        style="{",
    )
    return formatter


def get_streaming_spine_handler(stream=None):
    """
    Gets a handler that writes to a stream in the standard Spine/Splunk K=V format.
    Will use StreamHandler's default of sys.stderr if stream not provided.
    Similarly not responsible for opening / closing the stream as sderr/stdout
    can be passed.
    """
    stream_handler = SpineStreamHandler(stream)
    stream_handler.setFormatter(get_spine_splunk_formatter())
    return stream_handler


def get_log_base_config(log_config_paths):

    """
    Read the log base config
    - all the config is now read in at startup to move from a configparser
      object to a dictionary of tuples.
    This has a lower memory footprint (the difference in memory footprint
    is relevant to local builds - see SPII-18501)
    Args:
        log_config_paths (str or list of strings):
            Describes one or more paths containing log template config.
    """
    if not log_config_paths:
        return None

    # Use of str is required to support the case where a list of
    # log base config files have been provided
    log_base_dict = _LOG_BASE_CACHE.get(str(log_config_paths))
    if not log_base_dict:
        log_base_config = configparser.RawConfigParser()
        log_base_config.read(log_config_paths)
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

        _LOG_BASE_CACHE[str(log_config_paths)] = log_base_dict

    return log_base_dict


class SpineStreamHandler(StreamHandler):
    """
    Customised handler to modify routing and log levels of created records
    and generate any required additional logs.
    """

    def emit(self, record: LogRecord) -> None:
        """
        Intervene to write to different routing_keys with masked / unmasked
        data as appropriate
        """
        if self._call_emit():
            for log_record in self._create_additional_log_records(log_record=record):
                super().emit(log_record)

    def _call_emit(self):
        """
        atexit function in MeshClient attempts to log after pytest stream is closed and
        causes errors in test.
        The rest of the time self.stream will be either stdout or stderr and should
        never be closed.
        If either is closed, then we want to know about it.
        """
        if self.stream.closed:
            name = getattr(self.stream, "name")
            # True will let it raise when calling write() and subsequently hit
            # handleError, False will bypass the call to emit()
            return name and (name in [sys.stderr.name, sys.stdout.name])
        return True

    def _create_additional_log_records(self, log_record: LogRecord) -> List[LogRecord]:
        """
        Create any additional logs and make any required modifications
        to the source log.
        """
        log_records = []
        # Handle masked PID
        log_record, pid_record = self._re_route_pid_logs(log_record)
        if pid_record:
            log_records.append(pid_record)

        # Handle unexpected stack traces
        (
            log_record,
            crashdump_placeholder_record,
        ) = self._handle_crashdump_at_unexpected_level(log_record)
        if crashdump_placeholder_record:
            log_records.append(crashdump_placeholder_record)

        # TODO - write additional masked MONITOR logs if required for ITOC

        # Include the original (possibly modified) log
        log_records.append(log_record)
        return log_records

    @staticmethod
    def _re_route_pid_logs(log_record) -> Tuple[LogRecord, LogRecord]:
        """
        If the log contains data that has been masked, we want to send the unmasked log
        regardless of its level and intended route to the PID target.

        We will also route a masked version of the log to OPERATIONS.
        """
        pid_record = None
        if log_record.has_masked_data:
            # Create an additiona record
            # to log the unmasked data to PID
            pid_record = deepcopy(log_record)
            pid_record.level_name = "PID"
            pid_record.routing_key = LoggingConstants.LFR_PID
            pid_record.msg = pid_record.unmasked_log_line

            # write masked to OPERATIONS at INFO level
            log_record.level_name = "INFO"
            log_record.routing_key = LoggingConstants.LFR_OPERATIONS

        return log_record, pid_record

    @staticmethod
    def _handle_crashdump_at_unexpected_level(log_record: LogRecord):
        """
        If we find crashdump info at a unexpected level (i.e. INFO/DEBUG) we
        want to write a placeholder that we can make visible to non-SC cleared staff
        whilst routing the detailed information to CRASHDUMP
        """
        crashdump_placeholder_record = None
        crashdump_placeholder_log = getattr(
            log_record, "exc_info_placeholder_log_line", None
        )
        if crashdump_placeholder_log:
            # We can't just deepcopy as the traceback info causes problems
            crashdump_placeholder_record = LogRecord(
                log_record.name,
                log_record.levelno,
                log_record.pathname,
                log_record.lineno,
                log_record.exc_info_placeholder_log_line,
                None,
                None,
            )
            crashdump_placeholder_record.log_reference = LoggingConstants.LR_CRASHDUMP
            crashdump_placeholder_record.process_name = log_record.process_name
            crashdump_placeholder_record.level_name = "CRITICAL"
            crashdump_placeholder_record.routing_key = LoggingConstants.LFR_OPERATIONS

            # Route the original log to CRASHDUMP
            log_record.routing_key = LoggingConstants.LFR_CRASHDUMP

        return log_record, crashdump_placeholder_record


class SpineTemplateLoggerAdapter(LoggerAdapter):
    """Adapter to produce Spine style k=v logs from mustache template log files"""

    def __init__(
        self,
        logger,
        log_config_path=None,
        additional_log_config_paths=None,
        process_name="ANON",
    ):
        super().__init__(logger, dict(process_name=process_name))
        if not log_config_path:
            log_config_path = os.path.join(
                os.path.dirname(__file__), "cloudlogbase.cfg"
            )
        log_config_paths = [log_config_path]
        if additional_log_config_paths:
            log_config_paths.extend(additional_log_config_paths)
        self._log_base_dict = get_log_base_config(log_config_paths)
        self.process_name = process_name
        self._log_base_cache = {}

    def process(self, msg: str, kwargs: dict):
        """
        Override default `process` method because we want to get the log message
        template and the desired log level from a config file.
        """
        log_details = get_log_details(msg, self._log_base_dict, self._log_base_cache)
        if not log_details:
            return None, None

        # If not provided, set empty values for internalID and sessionId
        add_default_keys(kwargs)
        # and process pid, flagging as audit required if necessary
        evaluate_log_keys(log_details, kwargs)

        log_row_dict_masked = mask_url(kwargs)
        has_masked_data = log_row_dict_masked != kwargs
        masked_log_line = create_log_line(log_details.log_text, log_row_dict_masked)
        unmasked_log_line = ""
        if has_masked_data:
            unmasked_log_line = create_log_line(log_details.log_text, kwargs)

        # only retain the entries that are interesting to the python logging framework
        rv_dict = {}
        routing_key = self._evaluate_routing_key(log_details)
        enriched = {
            "log_reference": msg,
            "level_name": log_details.level_name,
            "has_masked_data": has_masked_data,
            "unmasked_log_line": unmasked_log_line,
            "routing_key": routing_key,
        }
        passed_extra = log_row_dict_masked.pop("extra", None)
        if not isinstance(passed_extra, dict):
            if passed_extra:
                enriched["extra"] = passed_extra
            passed_extra = {}
        if kwargs.get("exc_info") and log_details.level_value >= LoggingConstants.INFO:
            placeholder_details = get_log_details(
                LoggingConstants.LR_CRASHDUMP, self._log_base_dict, self._log_base_cache
            )
            placeholder_log_line = create_log_line(
                placeholder_details.log_text, {"originalLogReference": msg}
            )
            enriched["exc_info_placeholder_log_line"] = placeholder_log_line
        other_special = {
            k: v for k, v in log_row_dict_masked.items() if k in PYTHON_INSPECTED_ARGS
        }

        rv_dict = {**other_special, "extra": {**self.extra, **passed_extra, **enriched}}
        return masked_log_line, rv_dict

    def audit(self, msg, *args, **kwargs):
        """logs at a higher level that critical, i.e. always"""
        self.log(AUDIT, msg, *args, **kwargs)

    def _evaluate_routing_key(self, log_details: LogDetails):
        """BW TODO One of LFR_AUDIT, LFR_OPERATIONS, LFR_CRASHDUMP"""
        if log_details.audit_log_required:
            return LoggingConstants.LFR_AUDIT
        if log_details.monitor_log_required:
            return LoggingConstants.LFR_NMS
        if log_details.level_name == "PID":
            return LoggingConstants.LFR_PID

        return LoggingConstants.LFR_OPERATIONS


def get_spine_logger(
    stream=None,
    process_name=None,
    log_config_path=None,
    additional_log_config_paths=None,
):
    """
    Initialise a Spine-style logger that logs to a stream.
    Defaults to sys.stderr if no stream provided.
    """

    spine_logger = logging.getLogger(LoggingConstants.SPINE_LOGGER)
    spine_logger.propagate = False
    spine_logger.setLevel(logging.INFO)

    # Get a handler that writes to a stream in the format we understand
    handler = get_streaming_spine_handler(stream=stream)

    # add that handler to our logger
    spine_logger.addHandler(handler)

    # return the adapted logger thast adds Process/logRef/level to all logs

    return SpineTemplateLoggerAdapter(
        spine_logger,
        process_name=process_name,
        log_config_path=log_config_path,
        additional_log_config_paths=additional_log_config_paths,
    )
