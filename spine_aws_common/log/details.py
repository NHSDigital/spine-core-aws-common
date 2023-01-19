"""
Created 18th June 2019
"""
from copy import deepcopy

from spine_aws_common.log.constants import LoggingConstants


class LogDetails:
    """
    Object to hold certain log details
    """

    def __init__(
        self,
        log_text: str,
        level_value: int = LoggingConstants.INFO,
        level_name: str = "INFO",
        monitor_log_required=False,
        audit_log_required=False,
    ):
        # pylint:disable=too-many-arguments
        self.log_text = log_text
        self.level_value = level_value
        self.level_name = level_name
        self.monitor_log_required = monitor_log_required
        self.audit_log_required = audit_log_required

    def check_log_severity_for_log(
        self, severity_threshold_override, default_severity_threshold
    ):
        """Check to see if the log_value requires the message to be logged"""
        severity_threshold = severity_threshold_override or default_severity_threshold
        severity_threshold_value = return_level(severity_threshold)[0]

        # Log severity does not meet the severity threshold so ignore
        if self.level_value > severity_threshold_value:
            return False
        return True

    @staticmethod
    def check_log_severity_for_crashdump(
        severity_threshold_override, default_severity_threshold, error_list
    ):
        """
        If more than an INFO log an a traceback exists - produce a crashdump
        """
        severity_threshold = severity_threshold_override
        if not severity_threshold:
            severity_threshold = default_severity_threshold

        severity_threshold_value = return_level(severity_threshold)[0]
        if severity_threshold_value >= LoggingConstants.INFO and error_list:
            return True
        return False


def return_level(log_level):
    """
    Converts between Text and numeric form of syslog references
    """
    audit_log_required = False
    monitor_log_required = False

    if log_level == "AUDIT":
        log_value = LoggingConstants.AUDIT
        audit_log_required = True
    elif log_level == "AUDIT-MONITOR":
        log_value = LoggingConstants.AUDIT
        log_level = "AUDIT"
        audit_log_required = True
        monitor_log_required = True
    elif log_level == "INFO-MONITOR":
        log_value = LoggingConstants.INFO
        log_level = "INFO"
        monitor_log_required = True
    elif log_level == "CRITICAL":
        log_value = LoggingConstants.CRITICAL
    elif log_level == "ERROR":
        log_value = LoggingConstants.ERROR
    elif log_level == "WARN":
        log_value = LoggingConstants.WARN
    elif log_level in ["INFO", "INFORM"]:
        log_value = LoggingConstants.INFO
    elif log_level == "DEBUG":
        log_value = LoggingConstants.DEBUG
    elif log_level == "TRACE":
        log_value = LoggingConstants.TRACE
    else:
        log_value = LoggingConstants.AUDIT

    return log_value, log_level, monitor_log_required, audit_log_required


def get_log_details(log_reference: str, log_base_dict: dict, log_base_cache: dict):
    """
    Lookup the log text and severity for the specified log reference.
    Cache the outcome.
    """
    log_details_obj = log_base_cache.get(log_reference)

    if not log_details_obj:
        # Cache miss, build a LogDetails object from the config
        # Get the default UTI9999 error if we can't even find that.
        level_name, log_text = log_base_dict.get(
            log_reference, log_base_dict.get("UTI9999", ["INFO", "Missing default log"])
        )
        [
            level_value,
            level_name,
            monitor_log_required,
            audit_log_required,
        ] = return_level(level_name)

        log_details_obj = LogDetails(
            log_text, level_value, level_name, monitor_log_required, audit_log_required
        )
        log_base_cache[log_reference] = log_details_obj

    return deepcopy(log_details_obj)
