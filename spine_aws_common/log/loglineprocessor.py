"""
Created 18th June 2019
"""
from urllib.parse import urlsplit, parse_qs


class LogLineProcessor:
    """
    Class for applying log processing on a line by line basis.
    Cleansing of PID data is applied here. Specific keys can
    be passed to further processor classes if additional
    processing is required.
    """

    def __init__(self):
        self.processors = {}
        self.processor_keys = []

        self.pid_references = self.make_sensitive_substitutions()
        self.setprocessor_keys()

    @staticmethod
    def make_sensitive_substitutions():
        """
        List of substitution references - where patient identifiable data
        should be stripped from Operation Logs. Substitution is case
        insensitive.
        """
        # Force all keys to lower - they are compared against key.lower()
        return set(
            x.lower()
            for x in [
                "nhsNumber",
                "successorNhsNumber",
                "motherNhsNumber",
                "babyNhsNumber",
                # The following lines are output in Demographics Trace Logging
                "queryLine",
                "givenName",
                "familyName",
                # The following lines are output in CPIS Logging.
                "authIdentityNo",
                "laCode",
                "laName",
                "cpoType",
            ]
        )

    def setprocessor_keys(self):
        """
        List of keys which are subject to additional processing
        """
        self._add_processor("url", self.url_key_handler)
        self._add_processor("requestUrl", self.url_key_handler)

    def _add_processor(self, key, handler):
        """
        Add a processor and corresponding handler instance
        to the log processor.
        """
        lower_key = key.lower()
        self.processor_keys.append(lower_key)
        self.processors[lower_key] = handler

    # pylint: disable=broad-except
    # We really do want to catch a general exception in process().
    # There is scope for failures in the log key handlers which
    # would cause critical application errors. Since all logging
    # may pass through this method, validating all input edge cases
    # is difficult. It's safer to catch the general exception and
    # carry on as normal.
    def process(self, key, log_line):
        """
        Determine if we should process this type of key.
        If so, pass processing to the appropriate handler.
        """
        audit_row_required = False
        if not key:
            return audit_row_required

        lower = key.lower()

        if lower in self.pid_references:
            audit_row_required = True

        elif lower in self.processor_keys:
            try:
                audit_row_required = self.processors[lower](log_line)
            except Exception:
                pass

        return audit_row_required

    def url_key_handler(self, url):
        """
        Handler for url key types. Remove PID which
        has been passed as a URL parameter
        """
        query = urlsplit(url.lower())[3]
        params = parse_qs(query)

        return len(set(params.keys()) & self.pid_references) > 0


def check_for_param_dictionary(param_dict):
    """
    If key is 'parameters' and value is a dict, check the keys within the dict
    for any which need to be in audit.
    """
    if isinstance(param_dict, dict):
        for param_key in param_dict:
            audit = LogLineProcessor().process(param_key, param_dict[param_key])
            if audit:
                return True

    return False
