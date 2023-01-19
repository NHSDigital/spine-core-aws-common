""" Unit tests for masking"""
import pytest
from spine_aws_common.log.masking import mask_url


@pytest.mark.parametrize(
    "log_dict,expected_log_dict",
    [
        (
            # Masks url keys
            {"url": "/patient/search?nhsnumber=1234567890"},
            {"url": "/patient/search?nhsnumber=___MASKED___"},
        ),
        (
            # Masks requestUrl keys
            {"requestUrl": "/patient/search?nhsnumber=1234567890"},
            {"requestUrl": "/patient/search?nhsnumber=___MASKED___"},
        ),
        (
            # Doesn't mask key=value pairs
            {"nhsNumber": "1234567890"},
            {"nhsNumber": "1234567890"},
        ),
    ],
)
def test_mask_url(log_dict, expected_log_dict):
    """Basic testing of input masking"""

    # When
    masked_log_dict = mask_url(log_dict)

    # Then
    assert masked_log_dict == expected_log_dict
