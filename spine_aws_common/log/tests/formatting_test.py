""" Unit tests for PID masking """
from copy import deepcopy

import pytest

from spine_aws_common.log.details import LogDetails
from spine_aws_common.log.formatting import evaluate_log_keys


@pytest.mark.parametrize(
    "log_details,log_dict,expected_log_dict,audit_required",
    [
        (
            LogDetails(log_text="Log text with a placeholder={placeholder}"),
            {"placeholder": "PLACEHOLDER"},
            None,
            False,
        ),
        (
            LogDetails(log_text="Log text with likely pid nhsNumber={nhsNumber}"),
            {"nhsNumber": "1234567890"},
            None,
            True,
        ),
        (
            LogDetails(log_text="Log text with missing key provided value={value}"),
            {"value": ""},
            {"value": "NotProvided"},
            False,
        ),
    ],
)
def test_evaluate_log_keys(log_details, log_dict, expected_log_dict, audit_required):
    """Happy path test that PID gets recognised"""

    # When
    processed_log_dict = deepcopy(log_dict)
    evaluate_log_keys(log_details, processed_log_dict)

    # Then
    assert log_details.audit_log_required == audit_required

    if expected_log_dict:
        assert processed_log_dict == expected_log_dict
