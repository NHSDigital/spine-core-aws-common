"""
Created 18th June 2019
"""
import re
import six

from spine_aws_common.log.loglineprocessor import (
    check_for_param_dictionary,
    LogLineProcessor,
)


NOT_PROVIDED = "NotProvided"

DEFAULT_KEYS = ["internalID", "sessionid"]


def _default_key(log_row_dict, key, value):
    """
    If not already set, puts key=value into the dictionary: primarily useful
    for preventing key substitution errors for common fields.
    """
    if key not in log_row_dict:
        log_row_dict[key] = value


def _substitute_if_empty(value):
    """
    Splunk SDK version being used doesn't handle empty text nodes efficiently
    when parsing the results of a splunk query. This method substitutes any
    empty strings with text NotProvided.
    """
    if isinstance(value, six.string_types) and not value.strip():
        return NOT_PROVIDED
    return value


def add_default_keys(log_row_dict):
    """
    Add any default keys
    """
    for key in DEFAULT_KEYS:
        _default_key(log_row_dict, key, "")


def create_log_preamble(log_level, process_name, log_reference):
    """Creates the string to form the initial part of any log message"""
    return f"Log_Level={log_level} Process={process_name} logReference={log_reference}"


def can_encode_string(value):
    """
    Python 2 and 3 compatible check to see if value is either a base or
    unicode string.
    """
    return isinstance(value, str)


def _decode_unicode_dictionary(substitution_dict):
    """
    Resolve any unicode issues with the dictionary
    """
    decode_dict = {}
    for key in substitution_dict:
        if can_encode_string(substitution_dict[key]):
            decode_dict[key] = substitution_dict[key].encode("utf-8")
        else:
            decode_dict[key] = substitution_dict[key]
    return decode_dict


def evaluate_log_keys(log_details, log_row_dict):
    """
    Evaulate each log key to ensure no empty logs slip through
    """
    for log_key in log_row_dict:
        audit = check_for_param_dictionary(log_row_dict[log_key])
        log_details.audit_log_required = audit or log_details.audit_log_required

        audit = LogLineProcessor().process(log_key, log_row_dict[log_key])
        log_details.audit_log_required = audit or log_details.audit_log_required

        log_row_dict[log_key] = _substitute_if_empty(log_row_dict[log_key])


def create_log_line(log_preamble, log_text, substitution_dict):
    """
    Write a log line, catching error scenarios (unicode and missing terms in
    dictionary) and ensuring everything fits on a single line.
    """
    try:
        log_line = log_preamble + " - " + log_text.format(**substitution_dict)
    except KeyError as err:
        log_line = log_preamble + " - " + log_text + " - "
        log_line += "No substitution due to KeyError, missing keys: "
        log_line += str(list(err.args))
        log_line += ", dictionary of "
        log_line += str(substitution_dict)
        print("Substitution failure - fail build: " + log_line)
    except UnicodeError:
        decode_dict = _decode_unicode_dictionary(substitution_dict)
        log_line = log_preamble + " - " + log_text.format(**decode_dict)

    # Replace newlines with spaces
    log_line = re.sub(r"\n|\r", " ", log_line)
    return log_line


def substitute_preamble_for_monitor(log_preamble):
    """
    Switch the Log Level for the monitor version of info/audit log
    """
    if "Log_Level=AUDIT" in log_preamble:
        return log_preamble.replace("Log_Level=AUDIT", "Log_Level=MONITOR")
    if "Log_Level=INFO" in log_preamble:
        return log_preamble.replace("Log_Level=INFO", "Log_Level=MONITOR")
    return log_preamble
