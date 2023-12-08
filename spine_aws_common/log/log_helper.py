"""Test log helper to determine if correct logs and details were logged"""
from typing import Callable, Dict, Generator, Optional
import io
import re
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

    def find_log_entries(self, log_reference: str) -> Generator[Dict[str, str], None, None]:
        yield from self.log_entries(lambda line: f"logReference={log_reference} " in line)

    def log_entries(self, predicate: Optional[Callable[[str], bool]] = None):
        for line in self.log_lines(predicate):
            if not line:
                continue
            yield {
                k: v.strip("\"'")
                for k, v in (
                    match.split("=", maxsplit=1)
                    for match in re.findall(r'(?:\s|^)(\w+=(?:\'[^\']+\'|"[^"]+"|[^ ]+))', line)
                )
            }

    def log_lines(self, predicate: Optional[Callable[[str], bool]] = None) -> Generator[str, None, None]:
        content = self.captured_output.getvalue()
        for line in content.split("\n"):
            if not line:
                continue

            if not predicate or predicate(line):
                yield line

    def was_logged(self, log_reference):
        """Was a particular log reference logged"""
        if any(self.log_lines(lambda line: f"logReference={log_reference} " in line)):
            return True
        return False

    def was_value_logged(self, log_reference, key, value):
        """Was a particular key-value pair logged for a log reference"""
        for log_line in self.log_lines(lambda line: f"logReference={log_reference} " in line):
            if f"{key}={value}" in log_line:
                return True

        return False
