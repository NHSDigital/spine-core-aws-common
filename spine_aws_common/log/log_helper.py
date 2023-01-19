"""Test log helper to determine if correct logs and details were logged"""
import io
import sys
import logging
from spine_aws_common.log.spinelogging import (
    get_streaming_spine_handler,
    get_spine_splunk_formatter,
)


class LogHelper:
    """Log Helper"""

    def __init__(self) -> None:
        self.captured_output = None
        self.stream_handler = None

    def set_stream_capture(self):
        """Reset the stdout capture"""
        self.captured_output = io.StringIO()
        self.stream_handler = get_streaming_spine_handler(stream=self.captured_output)
        self.stream_handler.setFormatter(get_spine_splunk_formatter())
        spine_logger = logging.getLogger("SPINE")
        spine_logger.addHandler(self.stream_handler)

    def clean_up(self):
        """Cleanup after use and output for test results"""
        print(self.captured_output.getvalue(), file=sys.stderr)
        self.captured_output.close()
        spine_logger = logging.getLogger("SPINE")
        spine_logger.removeHandler(self.stream_handler)

    def was_logged(self, log_reference):
        """Was a particular log reference logged"""
        if any(
            f"logReference={log_reference} " in line for line in self.get_log_lines()
        ):
            return True
        return False

    def was_value_logged(self, log_reference, key, value):
        """Was a particular key-value pair logged for a log reference"""
        for log_line in self.get_log_lines():
            if f"logReference={log_reference} " not in log_line:
                continue

            if f"{key}={value}" in log_line:
                return True

        return False

    def get_log_lines(self):
        """Get the logs lines"""
        s = self.captured_output.getvalue()
        log_lines = [log_line for log_line in s.split("\n") if log_line]
        return log_lines


'18/01/2023 17:45:49.466 - Log_Level=INFO Process=AuditTest logReference=TESTMASKEDINFO001 - Info level log with message="this url might need masking" and data that may be masked url=/request/patient/search?nhsNumber=___MASKED___ for internalID=20210402275931855370_962FCF_2\rNoneType: None\n\n'
