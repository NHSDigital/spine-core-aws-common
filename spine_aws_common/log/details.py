"""
Created 18th June 2019
"""
from copy import deepcopy
import logging
import configparser as ConfigParser

from spine_aws_common.log.constants import LoggingConstants as lc


class LogDetails():
    """
    Object to hold certain log details
    """

    def __init__(
            self,
            log_text,
            log_value,
            log_level,
            monitor_log_required,
            audit_log_required
    ):
        # pylint:disable=too-many-arguments
        self.log_text = log_text
        self.log_value = log_value
        self.log_level = log_level
        self.monitor_log_required = monitor_log_required
        self.audit_log_required = audit_log_required

    def check_log_severity_for_log(
            self, severity_threshold_override, default_severity_threshold):
        """ Check to see if the log_value requires the message to be logged """
        severity_threshold = severity_threshold_override
        if not severity_threshold:
            severity_threshold = default_severity_threshold

        severity_threshold_value = return_level(severity_threshold)[0]

        # Log severity does not meet the severity threshold so ignore
        if self.log_value > severity_threshold_value:
            return False
        return True

    @staticmethod
    def check_log_severity_for_crashdump(
            severity_threshold_override,
            default_severity_threshold,
            error_list
    ):
        """
        If more than an INFO log an a traceback exists - produce a crashdump
        """
        severity_threshold = severity_threshold_override
        if not severity_threshold:
            severity_threshold = default_severity_threshold

        severity_threshold_value = return_level(severity_threshold)[0]
        if severity_threshold_value >= lc.INFO and error_list:
            return True
        return False


def return_level(log_level):
    """
    Converts between Text and numeric form of syslog references
    """
    audit_log_required = False
    monitor_log_required = False

    if log_level == 'AUDIT':
        log_value = lc.AUDIT
        audit_log_required = True
    elif log_level == 'AUDIT-MONITOR':
        log_value = lc.AUDIT
        log_level = 'AUDIT'
        audit_log_required = True
        monitor_log_required = True
    elif log_level == 'INFO-MONITOR':
        log_value = lc.INFO
        log_level = 'INFO'
        monitor_log_required = True
    elif log_level == 'CRITICAL':
        log_value = lc.CRITICAL
    elif log_level == 'ERROR':
        log_value = lc.ERROR
    elif log_level == 'WARN':
        log_value = lc.WARN
    elif log_level in ['INFO', 'INFORM']:
        log_value = lc.INFO
    elif log_level == 'DEBUG':
        log_value = lc.DEBUG
    elif log_level == 'TRACE':
        log_value = lc.TRACE
    else:
        log_value = lc.AUDIT

    return log_value, log_level, monitor_log_required, audit_log_required


def _get_log_details(
        log_reference, log_base_dict, log_base_cache, pythonlogging):
    """
    Lookup the log text and severity for the specified log reference.
    Cache the outcome to prevent repeated hits on the config object
    """
    log_details_obj = log_base_cache.get(log_reference)

    if not log_details_obj:
        # Cache miss
        log_info = log_base_dict.get(log_reference)
        if log_info:
            log_level, log_text = log_info
        else:
            log_level, log_text = log_base_dict.get(
                'LAMBDAUTI9999', ['INFO', 'Missing default log'])
            print('Missing log reference - fail build')

        [log_value,
         log_level,
         monitor_log_required,
         audit_log_required] = return_level(log_level)

        log_details_obj = LogDetails(
            log_text,
            log_value,
            log_level,
            monitor_log_required,
            audit_log_required
        )

        if pythonlogging:
            logger = logging.getLogger(lc.SPINE_LOGGER)
            logger.log_base_cache[log_reference] = log_details_obj
        else:
            log_base_cache[log_reference] = log_details_obj

    return deepcopy(log_details_obj)


def get_log_details(
        log_reference, log_base_dict, log_base_cache, pythonlogging=True):
    """
    Get the logging text and level details based on the log reference
    """
    try:
        log_details = _get_log_details(
            log_reference, log_base_dict, log_base_cache, pythonlogging)
    except ConfigParser.NoSectionError:
        log_row_dict = {}
        log_row_dict['logReference'] = log_reference
        log_reference = 'LAMBDAUTI9999'
        try:
            log_details = _get_log_details(
                log_reference, log_base_dict, log_base_cache, pythonlogging)
        except ConfigParser.NoSectionError:
            print('Log base does not contain mandatory LAMBDAUTI9999 entry')
            return None

    return log_details