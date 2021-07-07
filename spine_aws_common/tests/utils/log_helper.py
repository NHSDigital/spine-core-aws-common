"""Test log helper to determine if correct logs and details were logged"""
import io
import sys


class LogHelper:
    """Log Helper"""

    def __init__(self) -> None:
        self.captured_output = None
        self.captured_err_output = None

    def set_stdout_capture(self):
        """Reset the stdout capture"""
        self.captured_output = io.StringIO()
        self.captured_err_output = io.StringIO()
        sys.stdout = self.captured_output
        sys.stderr = self.captured_err_output

    def clean_up(self):
        """Cleanup after use and output for test results"""
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        print(self.captured_output.getvalue(), file=sys.stdout)
        print(self.captured_err_output.getvalue(), file=sys.stderr)
        self.captured_output.close()
        self.captured_err_output.close()

    def was_logged(self, log_reference):
        """Was a particular log reference logged"""
        if any(
            f"logReference={log_reference}" in line for line in self._get_log_lines()
        ):
            return True
        return False

    def was_value_logged(self, log_reference, key, value):
        """Was a particular key-value pair logged for a log reference"""
        for log_line in self._get_log_lines():
            if f"logReference={log_reference}" not in log_line:
                continue

            if f"{key}={value}" in log_line:
                return True

        return False

    def _get_log_lines(self):
        """Get the logs lines"""
        return [
            log_line
            for log_line in self.captured_output.getvalue().split("\n")
            if log_line
        ]
