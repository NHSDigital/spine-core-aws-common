"""
Cloud logging module
"""
# Set imports to absolute values to avoid confusion between identical package names
from __future__ import absolute_import, print_function

import datetime
import traceback
import os

from spine_aws_common.log.spinelogging import get_log_base_config
from spine_aws_common.log.details import get_log_details, return_level
from spine_aws_common.log.constants import LoggingConstants
from spine_aws_common.log.formatting import (
    add_default_keys,
    evaluate_log_keys,
    create_log_line,
    substitute_preamble_for_monitor,
)
from spine_aws_common.log.thirdpartylogging import SEVERITY_INPUT_MAP, LoggingAdapter
from spine_aws_common.log.masking import mask_url


# pylint: disable=wrong-import-order
import logging as pythonlogging

# pylint: enable=wrong-import-order


class Logger:
    """
    Standard class for handling logging within cloud application
    Logs need to be prepared ready for splunk in the same way as
    Spine applications
    """

    _WRITEPLACEHOLDER = True  # Should a placeholder be written into operational logs

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        additional_log_config=None,
        log_base=os.path.join(os.path.dirname(__file__), "cloudlogbase.cfg"),
        process_name="ANON",
        severity_threshold="INFO",
        internal_id=None,
    ):
        self._log_base_dict = get_log_base_config(log_base=log_base)
        if additional_log_config:
            self._log_base_dict.update(
                get_log_base_config(log_base=additional_log_config)
            )

        self.process_name = process_name
        self.internal_id = internal_id
        self.severity_threshold = severity_threshold
        self.severity_threshold_value = return_level(severity_threshold)[0]
        self.date_format = "%d/%m/%Y %H:%M:%S"

        self._log_base_cache = {}

    def set_internal_id(self, internal_id):
        """Set internal ID"""
        self.internal_id = internal_id

    def set_process_name(self, process_name):
        """Set process name"""
        self.process_name = process_name

    def write_log(
        self,
        log_reference="UTI9999",
        error_list=None,
        log_row_dict=None,
        severity_threshold_override=None,
        process_name=None,
    ):
        """
        The writing of the log allows the following information to be passed:
        :param log_reference: this should resolve to a log_reference within the logBase
        :type  log_reference: str
        :param error_list: the output of a sys.exc_info() where an exception has been
        caught
        :param log_row_dict - a dictionary of substitutions to be made against the
        logText in the log_reference
        :type log_row_dict: dict
        :param severity_threshold_override: Not normally present - allows the standard
        log level to be over-ridden for this entry
        :param process_name: Not normally present - allows the standard process_name to
        be over-ridden for this entry
        The process for writing a log file entry is:
        Lookup the log reference information in the log base
        Exit out if the log level of the log is above that at which the user is set
        to log (e.g. if it is a DEBUG log and the user level is set to INFO)
        Create an audit version of the log_row_dict containing sensitive data, and
        determine if an Audit entry is required
        """
        if log_row_dict is None:
            log_row_dict = {}

        if process_name is None:
            process_name = self.process_name

        if not self._log_base_dict:
            self._print_output(process_name, log_reference, log_row_dict, error_list)
            return None

        log_details = get_log_details(
            log_reference,
            self._log_base_dict,
            self._log_base_cache,
            pythonlogging=False,
        )
        if not log_details or not log_details.check_log_severity_for_log(
            severity_threshold_override, self.severity_threshold
        ):
            return None

        # If not provided, set empty values for internalID and sessionId
        add_default_keys(log_row_dict)
        evaluate_log_keys(log_details, log_row_dict)

        time_now = datetime.datetime.now()
        log_preamble = self._create_log_preamble(
            time_now, log_details.log_level, process_name, log_reference
        )
        log_row_dict_masked = mask_url(log_row_dict)

        if log_details.audit_log_required:
            self._write_to_cloudwatch(
                log_preamble,
                log_details.log_text,
                log_row_dict_masked,
                LoggingConstants.LFR_AUDIT,
            )
        else:
            self._write_to_cloudwatch(
                log_preamble,
                log_details.log_text,
                log_row_dict_masked,
                LoggingConstants.LFR_OPERATIONS,
            )

        if log_details.monitor_log_required:
            # Swap to Log_Level=MONITOR - will help prevent SALTing requirement
            # As Splunk may get matching CRC check for Audit and Monitor Log
            self._write_to_cloudwatch(
                substitute_preamble_for_monitor(log_preamble),
                log_details.log_text,
                log_row_dict_masked,
                LoggingConstants.LFR_NMS,
            )

        if log_details.check_log_severity_for_crashdump(
            severity_threshold_override, self.severity_threshold, error_list
        ):
            stub_log_reference = LoggingConstants.LR_CRASHDUMP
            stub_log_details = get_log_details(
                stub_log_reference,
                self._log_base_dict,
                self._log_base_cache,
                pythonlogging=False,
            )
            stub_log_preamble = self._create_log_preamble(
                time_now, stub_log_details.log_level, process_name, stub_log_reference
            )

            # Write stub crashdump to spinevfmoperations, so that non-SC cleared staff
            # can see a crash occurred
            self._write_to_cloudwatch(
                stub_log_preamble,
                stub_log_details.log_text,
                {"originalLogReference": log_reference},
                LoggingConstants.LFR_OPERATIONS,
            )

            # Write actual crashdump to spinevfmcrashdump
            self._write_to_cloudwatch(
                log_preamble,
                log_details.log_text,
                log_row_dict,
                LoggingConstants.LFR_CRASHDUMP,
                error_list,
            )

        return log_details.log_text

    @staticmethod
    def _print_output(process_name, log_reference, log_row_dict, error_list):
        """
        Print out error details as no log object
        """
        print_string = process_name + ": Log Reference of " + str(log_reference)
        print_string += " raised but insufficient logging details"
        print_string += " identified to write to file."
        print(print_string)
        print("Error details " + str(error_list))
        print("Log Parameters " + str(log_row_dict))

    def _create_log_preamble(self, time_now, log_level, process_name, log_reference):
        """
        Creates the string to form the initial part of any log message
        """
        log_timestamp_string = time_now.strftime(self.date_format) + "."
        log_timestamp_string += str(int(time_now.microsecond / 1000)).rjust(3, "0")

        log_preamble = log_timestamp_string + " Log_Level=" + log_level
        log_preamble = log_preamble + " Process=" + str(process_name)
        if self.internal_id:
            log_preamble = log_preamble + " internalID=" + self.internal_id
        return log_preamble + " logReference=" + str(log_reference)

    @staticmethod
    def _write_to_cloudwatch(
        log_preamble,
        log_text,
        substitution_dict,
        log_type,
        error_list=None,
    ):
        """
        Writes the log out to the standard out for Cloudwatch logging
        """
        log_line = create_log_line(log_preamble, log_text, substitution_dict)
        if error_list is not None:
            log_line = log_line + " - " + str(error_list[0:])
        print(log_line)

        if (
            log_type == LoggingConstants.LFR_CRASHDUMP
            and error_list
            and len(error_list) >= 3
        ):
            exception, value, trace = error_list
            formatted_exception = " ".join(
                traceback.format_exception(exception, value, trace)
            )
            exception_line = create_log_line(log_preamble, formatted_exception, {})
            print(exception_line)


def configure_logging_adapter(log_object):
    """
    Configure an adapter to allow libraries that use standard Python logging to output
    to our log files
    """
    root_logger = pythonlogging.getLogger()
    root_logger.handlers = []
    root_logger.setLevel(SEVERITY_INPUT_MAP[log_object.severity_threshold])

    adapter = LoggingAdapter(log_object)
    root_logger.addHandler(adapter)
    root_logger.propagate = False
