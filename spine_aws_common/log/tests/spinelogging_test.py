""" Unit tests for Spine-style python logging """

import io
import logging
from logging import LoggerAdapter
import os
from os import path
from typing import Callable, Generator, Tuple

import pytest
from freezegun import freeze_time
from spine_aws_common.log.spinelogging import (
    get_spine_splunk_formatter,
    get_streaming_spine_handler,
    SPINE_SPLUNK_DATEFORMAT,
    get_spine_logger,
    SpineTemplateLoggerAdapter,
)
from spine_aws_common.log.details import LogDetails, get_log_details
from spine_aws_common.log.constants import LoggingConstants
from spine_aws_common.log.log_helper import LogHelper

from spine_aws_common.log.spinelogging import get_log_base_config

CORE_LOG_CONFIG = {
    "TESTCRITICAL001": [
        "CRITICAL",
        'Critical level log with message="{message}" for internalID={internalID}',
    ],
    "TESTDEBUG001": [
        "DEBUG",
        'Debug level log with message="{message}" for internalID={internalID}',
    ],
    "TESTINFO001": [
        "INFO",
        'Info level log with message="{message}" for internalID={internalID}',
    ],
    "TESTAUDIT001": [
        "AUDIT",
        'Audit level log with message="{message}" for internalID={internalID}',
    ],
    "TESTMASKEDINFO001": [
        "INFO",
        (
            'Log with message="{message}" and data that may be masked url={url} '
            "for internalID={internalID}"
        ),
    ],
    "TESTMASKEDAUDIT001": [
        "AUDIT",
        (
            'Log with message="{message}" and data that may be masked url={url} '
            "for internalID={internalID}"
        ),
    ],
    "UTI9992": [
        "CRITICAL",
        (
            "Crash dump occurred. See crashdump index for details "
            "with originalLogReference={originalLogReference}"
        ),
    ],
}

APP_SPECIFIC_CONFIG = {
    "APPCRITICAL001": [
        "CRITICAL",
        (
            "Application-specific Critical level log with "
            'message="{message}" for internalID={internalID}'
        ),
    ],
    "APPDEBUG001": [
        "DEBUG",
        (
            "Application-specific Debug level log with "
            'message="{message}" for internalID={internalID}'
        ),
    ],
    "APPINFO001": [
        "INFO",
        (
            "Application-specific Info level log with "
            'message="{message}" for internalID={internalID}'
        ),
    ],
}


@pytest.fixture(name="log_helper", scope="function")
def loghelper_fixture() -> Generator[LogHelper, None, None]:
    """LogHelper fixture"""
    log_helper = LogHelper()
    log_helper.set_stream_capture()
    yield log_helper
    log_helper.clean_up()


@pytest.fixture(name="log_path")
def log_path_fixture():
    """Convenience to consistently evaluate local testdata directory"""

    def factory(filename="testlog.cfg"):
        return path.join(path.dirname(__file__), "testdata", filename)

    return factory


@pytest.fixture(name="spine_logger")
def logger_fixture(log_path: str) -> Callable:
    """Fixture to provide a factory method for creating a spine logger"""

    def factory(**kwargs) -> LoggerAdapter:
        if "log_config_path" not in kwargs:
            kwargs["log_config_path"] = log_path()
        return get_spine_logger(**kwargs)

    return factory


def test_get_log_base_config(log_path: Callable):
    """Happy path test we get some config given a valid path"""
    # Given
    log_config_paths = log_path("testlog.cfg")

    # When
    actual = get_log_base_config(log_config_paths)

    # Then
    assert actual == CORE_LOG_CONFIG


def test_get_multiple_source_log_base_config(log_path: Callable):
    """Test that we get all the config given multiple valid paths"""
    # Given
    log_config_path = log_path("testlog.cfg")
    app_log_config_path = log_path("applog.cfg")

    # When
    actual = get_log_base_config([log_config_path, app_log_config_path])

    # Then
    assert actual == {**CORE_LOG_CONFIG, **APP_SPECIFIC_CONFIG}


def test_get_stdout_spine_handler():
    """Check some basic things about the handler we're getting"""
    # When
    handler = get_streaming_spine_handler()

    # Then
    assert handler.formatter.datefmt == SPINE_SPLUNK_DATEFORMAT


def test_get_spine_splunk_formatter():
    """Check some basic things about the formatter we're getting"""
    # When
    formatter = get_spine_splunk_formatter()

    # Then
    assert formatter.datefmt == SPINE_SPLUNK_DATEFORMAT


@pytest.mark.parametrize(
    "log_config_name,num_lines",
    [(None, None), ("testlog.cfg", 3), ("applog.cfg", 3)],
)
def test_get_logger(
    spine_logger: Callable, log_path: Callable, log_config_name: str, num_lines: int
):
    """Check some basic things about the logger we're getting"""
    # Given
    if not log_config_name or log_config_name == "cloudlogbase.cfg":
        log_file_path = os.path.join(
            os.path.dirname(__file__), "..", "cloudlogbase.cfg"
        )
    else:
        log_file_path = log_path(log_config_name)

    # When
    logger = spine_logger(log_config_path=log_file_path)

    # Then
    assert isinstance(logger, SpineTemplateLoggerAdapter)
    assert logger.name == LoggingConstants.SPINE_LOGGER
    assert logger.logger.name == LoggingConstants.SPINE_LOGGER

    with open(log_file_path, encoding="utf-8") as logbase:
        lines = [line for line in logbase.readlines() if line.startswith("[")]
        num_lines = len(lines)

    assert len(logger._log_base_dict.keys()) == num_lines


@freeze_time("2023-01-12 01:22:11.578")
def test_no_log_propagation(spine_logger: Callable, log_helper: Generator):
    """
    Test that these specifically formatted strings don't get passed to other loggers
    """
    # Given
    spine_logger = spine_logger(process_name="TestPropagate")
    # When
    other_logger = logging.getLogger("MyOtherLogger")
    other_logger.setLevel(logging.INFO)
    other_stream = io.StringIO()
    other_stream_handler = logging.StreamHandler(other_stream)
    other_logger.addHandler(other_stream_handler)
    other_logger.info("Some text and some %s", "dynamic text")
    spine_logger.info(
        "TESTINFO001",
        message="I only understand preconfigured templates",
        internalID="2023011701015900",
    )

    # Then
    log_lines = log_helper.get_log_lines()
    assert len(log_lines) == 1
    assert log_lines[0] == (
        "12/01/2023 01:22:11.578 - "
        "Log_Level=INFO Process=TestPropagate logReference=TESTINFO001 - "
        'Info level log with message="I only understand preconfigured templates" '
        "for internalID=2023011701015900"
    )
    assert other_stream_handler.stream.getvalue() == "Some text and some dynamic text\n"


@pytest.mark.parametrize(
    "log_reference, expected_log_details",
    [
        (
            "TEST1234",
            LogDetails("Missing default log"),
        ),
        (
            "KNOWNLOG1",
            LogDetails("A log with placeholder={placeholder} uncached"),
        ),
        (
            "KNOWNLOG2",
            LogDetails("A log with placeholder={placeholder} cached"),
        ),
        (
            "KNOWNLOG3",
            LogDetails(
                "An audit log with placeholder={placeholder} uncached",
                level_value=LoggingConstants.AUDIT,
                level_name="AUDIT",
                audit_log_required=True,
            ),
        ),
        (
            "KNOWNLOG4",
            LogDetails(
                "An audit log with placeholder={placeholder} cached",
                level_value=LoggingConstants.AUDIT,
                level_name="AUDIT",
                audit_log_required=True,
            ),
        ),
        (
            "KNOWNLOG5",
            LogDetails(
                "An info-monitor log with placeholder={placeholder} uncached",
                level_name="INFO",
                monitor_log_required=True,
            ),
        ),
    ],
)
def test_get_log_details(log_reference: str, expected_log_details: LogDetails):
    """Test getting a LogDetails object given a log reference"""
    # Given
    log_base_dict = {
        "KNOWNLOG1": ["INFO", "A log with placeholder={placeholder} uncached"],
        "KNOWNLOG2": ["INFO", "A log with placeholder={placeholder} cached"],
        "KNOWNLOG3": ["AUDIT", "An audit log with placeholder={placeholder} uncached"],
        "KNOWNLOG4": ["AUDIT", "An audit log with placeholder={placeholder} cached"],
        "KNOWNLOG5": [
            "INFO-MONITOR",
            "An info-monitor log with placeholder={placeholder} uncached",
        ],
    }
    log_base_cache = {
        "KNOWNLOG2": LogDetails("A log with placeholder={placeholder} cached"),
        "KNOWNLOG4": LogDetails(
            "An audit log with placeholder={placeholder} cached",
            level_value=LoggingConstants.AUDIT,
            level_name="AUDIT",
            audit_log_required=True,
        ),
    }

    # When
    actual = get_log_details(log_reference, log_base_dict, log_base_cache)

    # Then
    assert actual
    assert isinstance(actual, LogDetails)

    assert actual.log_text == expected_log_details.log_text
    assert actual.level_value == expected_log_details.level_value
    assert actual.level_name == expected_log_details.level_name
    assert actual.audit_log_required == expected_log_details.audit_log_required
    assert actual.monitor_log_required == expected_log_details.monitor_log_required


@pytest.mark.parametrize(
    "log_reference, log_params,expected_log_text",
    [
        (
            "TESTCRITICAL001",
            {"message": "Something bad happened", "exc_info": True},
            (
                'Critical level log with message="Something bad happened" '
                "for internalID=NotProvided"
            ),
        ),
        (
            "UNKNOWN001",
            {"other": "junk"},
            "Missing default log",
        ),
    ],
)
def test_spine_logging_adapter_process(
    spine_logger: Callable,
    log_reference: str,
    log_params: dict,
    expected_log_text: str,
):
    """Test the Spine logger adapter processing"""
    # Given
    logger_adapter = spine_logger(process_name="AdapterTest")

    # When
    actual_log_message, retained_args = logger_adapter.process(
        log_reference, log_params
    )

    # Then
    assert actual_log_message == expected_log_text
    python_logging_special_keys = sorted(
        ["exc_info", "extra", "stack_info", "stacklevel"]
    )
    # Assert no other keys are retained
    assert set(retained_args.keys()) - set(python_logging_special_keys) == set()


@freeze_time("2022-01-19 13:40:06.001")
def test_usage(spine_logger: Callable, log_helper: LogHelper):
    """Test how a client consumer would use the spine logger"""
    # Given
    process_name = "UsageTest"
    logger = spine_logger(process_name=process_name)
    log_reference = "TESTINFO001"
    message = "Hello there"
    internal_id = "20230113155042966481_962FCF_2"

    # When
    logger.info(
        log_reference,
        **{"message": message, "internalID": internal_id},
    )
    # Then
    log_lines = log_helper.get_log_lines()
    assert log_lines[0] == (
        "19/01/2022 13:40:06.001"
        f" - Log_Level=INFO Process={process_name} logReference={log_reference}"
        " - Info level log with"
        f' message="{message}" for internalID={internal_id}'
    )


@freeze_time("2021-11-03 17:03:15.105", tz_offset=-1)
def test_exception_handling(spine_logger: Callable, log_helper: LogHelper):
    """Test exception handling from the top down"""
    # Given
    process_name = "ExceptionTest"
    logger = spine_logger(process_name=process_name)
    log_reference = "TESTCRITICAL001"
    message = "A bad error"
    internal_id = "20221009275931855370_962FCF_2"

    # When
    try:
        raise Exception("We didn't expect this to happpen")
    except Exception:
        logger.critical(
            log_reference, message=message, internalID=internal_id, exc_info=1
        )
    # Then
    log_lines = log_helper.get_log_lines()
    assert len(log_lines) == 1
    log_sections = log_lines[0].split("\r")
    assert log_sections[0] == (
        "03/11/2021 17:03:15.105"
        f" - Log_Level=CRITICAL Process={process_name} logReference={log_reference}"
        " - Critical level log with"
        f' message="{message}" for internalID={internal_id}'
    )
    assert log_sections[1] == "Traceback (most recent call last):"
    # Can't be sure about individual bits of stack trace,
    # paths are dependant on environment
    assert (
        log_sections[-2] == '    raise Exception("We didn\'t expect this to happpen")'
    )
    assert log_sections[-1] == "Exception: We didn't expect this to happpen"


@freeze_time("2018-12-25 01:12:25.345", tz_offset=-1)
def test_exception_handling_with_placeholder(
    spine_logger: Callable, log_helper: LogHelper
):
    """Test exception writes a placeholder when theres a stack trace at a lower level"""
    # Given
    process_name = "ExceptionPlaceholderTest"
    logger = spine_logger(
        process_name=process_name,
    )
    log_reference = "TESTINFO001"
    message = "We shouldn't get errors in these logs"
    internal_id = "20230109275931855370_962FCF_2"

    # When
    try:
        raise Exception("We didn't expect this to happpen")
    except Exception:
        logger.info(log_reference, message=message, internalID=internal_id, exc_info=1)
    # Then
    log_lines = log_helper.get_log_lines()
    assert len(log_lines) == 2

    # Placeholder
    assert log_lines[0] == (
        "25/12/2018 01:12:25.345 - Log_Level=CRITICAL Process=ExceptionPlaceholderTest "
        "logReference=UTI9992 - Crash dump occurred. "
        "See crashdump index for details "
        f"with originalLogReference={log_reference}"
    )
    # Log_line 2 will contain the stack trace
    log_sections = log_lines[1].split("\r")
    assert log_sections[0] == (
        "25/12/2018 01:12:25.345"
        f" - Log_Level=INFO Process={process_name} logReference={log_reference}"
        " - Info level log with"
        f' message="{message}" for internalID={internal_id}'
    )
    assert log_sections[1] == "Traceback (most recent call last):"
    # Can't be sure about individual bits of stack trace,
    # paths are dependant on environment
    assert (
        log_sections[-2] == '    raise Exception("We didn\'t expect this to happpen")'
    )
    assert log_sections[-1] == "Exception: We didn't expect this to happpen"


@freeze_time("2019-02-16 08:32:54.543")
@pytest.mark.parametrize(
    "log_reference,message,url_tuple,internal_id",
    [
        (
            "TESTMASKEDINFO001",
            "this url might need masking",
            (
                "/request/patient/search?nhsNumber=123456789",
                "/request/patient/search?nhsNumber=___MASKED___",
            ),
            "20210402275931855370_962FCF_2",
        ),
        (
            "TESTMASKEDAUDIT001",
            "this url might need masking",
            (
                "/request/patient/search?nhsNumber=123456789",
                "/request/patient/search?nhsNumber=___MASKED___",
            ),
            "20210402275931855370_962FCF_2",
        ),
    ],
)
def test_masked_info_log_handling(
    spine_logger: Callable,
    log_helper: LogHelper,
    log_reference: str,
    message: str,
    url_tuple: Tuple[str, str],
    internal_id: str,
):
    """
    Test that an INFO level log with masked PID creates a copy of the record and
    routes an unmasked version to PID and the masked version to OPERATIONS.
    """
    # Given
    process_name = "AutoAuditTest"
    logger = spine_logger(process_name=process_name)
    url, url_masked = url_tuple

    # When
    logger.info(log_reference, message=message, url=url, internalID=internal_id)

    # Then
    log_lines = log_helper.get_log_lines()
    assert len(log_lines) == 2
    assert log_lines[1] == (
        "16/02/2019 08:32:54.543"
        f" - Log_Level=INFO Process={process_name} logReference={log_reference}"
        f' - Log with message="{message}" '
        f"and data that may be masked url={url_masked} for internalID={internal_id}"
    )
    assert log_lines[0] == (
        "16/02/2019 08:32:54.543"
        f" - Log_Level=PID Process={process_name} logReference={log_reference}"
        f' - Log with message="{message}" '
        f"and data that may be masked url={url} for internalID={internal_id}"
    )


@freeze_time("2020-01-14 18:22:32.111")
def test_unmasked_audit_log_handling(spine_logger: Callable, log_helper: LogHelper):
    """
    Test that an AUDIT level log with unmasked data does not get interfered with and
    just routes the unmodifed data to AUDIT
    """
    # Given
    process_name = "AuditTest"
    logger = spine_logger(process_name=process_name)
    log_reference = "TESTAUDIT001"
    message = "Some audit log message content"
    internal_id = "20210402275931855370_962FCF_2"

    # When
    logger.audit(log_reference, message=message, internalID=internal_id)

    # Then
    log_lines = log_helper.get_log_lines()
    assert len(log_lines) == 1
    assert log_lines[0] == (
        "14/01/2020 18:22:32.111"
        f" - Log_Level=AUDIT Process={process_name} logReference={log_reference}"
        f' - Audit level log with message="{message}"'
        f" for internalID={internal_id}"
    )
