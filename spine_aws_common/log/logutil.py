"""
New Logging Attempts
"""
from spine_aws_common.log.spinelogging import SpineLogger
from spine_aws_common.log.constants import LoggingConstants
from spine_aws_common.log.details import get_log_details
from spine_aws_common.log.formatting import (
    add_default_keys,
    create_log_preamble,
    evaluate_log_keys,
    substitute_preamble_for_monitor,
)
from spine_aws_common.log.masking import mask_url
from spine_aws_common.log.writer import write_to_file


def write_log(
    log_reference="UTI9999",
    error_list=None,
    log_row_dict=None,
    severity_threshold_override=None,
    process_name=None,
):
    """
    The writing of the log allows the following information to be passed:
    :param log_reference: this should resolve to a logReference within the
    logBase
    :type  log_reference: str
    :param error_list: the output of a sys.exc_info() where an exception has
    been caught
    :param log_row_dict - a dictionary of substitutions to be made against the
    logText in the logReference
    :type log_row_dict: dict
    :param severity_threshold_override: Not normally present - allows the
    standard log level to be over-ridden for this entry
    :param process_name: Not normally present - allows the standard processName
    to be over-ridden for this entry
    The process for writing a log file entry is:
    Lookup the log reference information in the log base
    Exit out if the log level of the log is above that at which the user is set
    to log (e.g. if it is a DEBUG log and the user level is set to INFO)
    Create an audit version of the log_row_dict containing sensitive data, and
    determine if an Audit entry is required.
    """
    if log_row_dict is None:
        log_row_dict = {}

    if process_name is None:
        process_name = SpineLogger.get_process_name()

    log_details = get_log_details(
        log_reference, SpineLogger.get_log_base_dict(), SpineLogger.get_log_base_cache()
    )
    if not log_details or not log_details.check_log_severity_for_log(
        severity_threshold_override, SpineLogger.get_severity_threshold()
    ):
        return None

    # If not provided, set empty values for internalID and sessionId
    add_default_keys(log_row_dict)

    evaluate_log_keys(log_details, log_row_dict)

    log_preamble = create_log_preamble(
        log_details.log_level, process_name, log_reference
    )
    log_row_dict_masked = mask_url(log_row_dict)

    if log_details.audit_log_required:
        write_to_file(
            log_preamble,
            log_details.log_text,
            log_row_dict_masked,
            LoggingConstants.LFR_AUDIT,
        )
    else:
        write_to_file(
            log_preamble,
            log_details.log_text,
            log_row_dict_masked,
            LoggingConstants.LFR_OPERATIONS,
        )

    if log_details.monitor_log_required:
        # Swap to Log_Level=MONITOR - will help prevent SALTing requirement
        # As Splunk may get matching CRC check for Audit and Monitor Log.
        write_to_file(
            substitute_preamble_for_monitor(log_preamble),
            log_details.log_text,
            log_row_dict_masked,
            LoggingConstants.LFR_NMS,
        )

    if log_details.check_log_severity_for_crashdump(
        severity_threshold_override, SpineLogger.get_severity_threshold(), error_list
    ):
        stub_log_reference = LoggingConstants.LR_CRASHDUMP
        stub_log_details = get_log_details(
            stub_log_reference,
            SpineLogger.get_log_base_dict(),
            SpineLogger.get_log_base_cache(),
        )
        stub_log_preamble = create_log_preamble(
            stub_log_details.log_level, process_name, stub_log_reference
        )

        # Write stub crashdump to spinevfmoperations, so that non-SC cleared
        # staff can see a crash occurred.
        write_to_file(
            stub_log_preamble,
            stub_log_details.log_text,
            {"originalLogReference": log_reference},
            LoggingConstants.LFR_OPERATIONS,
        )

        # Write actual crashdump.
        write_to_file(
            log_preamble,
            log_details.log_text,
            log_row_dict,
            LoggingConstants.LFR_CRASHDUMP,
            error_list,
        )

    return log_details.log_text
