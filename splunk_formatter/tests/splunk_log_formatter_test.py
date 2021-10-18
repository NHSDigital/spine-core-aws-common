import json
import os

import pytest
from splunk_formatter.tests.conftest import (
    generate_data_message,
    INCOMING_CONTROL_EVENT,
)


@pytest.mark.parametrize(
    "given_log_group,given_prefix,expected",
    (
        ("UploaderLambdaLogs", "test", "test:aws:cloudwatch_logs"),
        ("UploaderLambdaLogs", None, "aws:cloudwatch_logs"),
        ("MainCloudTrailLogs", "test", "test:aws:cloudtrail"),
        ("MainVPCLogs", "test", "test:aws:cloudwatch_logs:vpcflow"),
    ),
)
def test_get_source_type(app, given_log_group, given_prefix, expected):
    source_type = app.get_source_type(given_log_group, given_prefix)
    assert source_type == expected


def test_get_splunk_indexes_to_logs_levels(app):
    given = os.environ["SPLUNK_INDEXES_TO_LOGS_LEVELS"]
    expected = {"aws": "aws_test", "audit": "audit_test", "default": "app_test"}

    mappings = app.get_splunk_indexes_to_logs_levels(given)
    assert mappings == expected


@pytest.mark.parametrize(
    "given_log_level,given_index_mappings,expected",
    (
        (
            "AUDIT",
            {"aws": "aws_test", "audit": "audit_test", "default": "app_test"},
            "audit_test",
        ),
        (
            "UNKNOWN",
            {
                "aws": "aws_test",
                "audit": "audit_test",
                "default": "app_test",
            },
            None,
        ),
    ),
)
def test_get_index(app, given_log_level, given_index_mappings, expected):
    index = app.get_index(given_log_level, given_index_mappings)
    assert index == expected


@pytest.mark.parametrize(
    "given,expected",
    (
        (
            "15/10/2021 14:10:13.692 Log_Level=INFO Process=test-lr_02_validate_and_parse internalID=20211015141013691760_0CF842 logReference=LR02I01 - Something has happened",
            "INFO",
        ),
        (
            "15/10/2021 14:10:13.692 Log_Level=WARNING Process=test-lr_02_validate_and_parse internalID=20211015141013691760_0CF842 logReference=LAMBDA9999 - Probably not a good thing",
            "WARNING",
        ),
        (
            "15/10/2021 14:10:13.692 Log_Level=ERROR Process=test-lr_02_validate_and_parse internalID=20211015141013691760_0CF842 logReference=LAMBDA9999 - An error has occurred, shutting down",
            "ERROR",
        ),
        (
            "15/10/2021 14:10:13.692 Log_Level=CRITICAL Process=test-lr_02_validate_and_parse internalID=20211015141013691760_0CF842 logReference=LAMBDA9999 - Big error",
            "CRITICAL",
        ),
        (
            "15/10/2021 14:10:13.692 Log_Level=AUDIT Process=test-lr_02_validate_and_parse internalID=20211015141013691760_0CF842 logReference=LAMBDA9999 - This is a sensitive log line",
            "AUDIT",
        ),
        (
            "REPORT RequestId: 97c94011-4400-406e-abb4-343cc9d4d22b Duration: 2.07 ms Billed Duration: 3 ms Memory Size: 128 MB Max Memory Used: 75 MB",
            "AWS",
        ),
        (
            "15/10/2021 14:10:13.692 Log_Level=OMG Process=test-lr_02_validate_and_parse internalID=20211015141013691760_0CF842 logReference=LAMBDA9999 - This is a suprising log line",
            "UNKNOWN",
        ),
        (
            "Well this should probably not be a log line",
            "UNKNOWN",
        ),
    ),
)
def test_get_level_of_log(app, given, expected):
    level = app.get_level_of_log(given)
    assert level == expected


def test_process_records_log_message(app_initialised):
    """Testing the processing of incoming records with actual data message which gets accepted"""
    expected_record = {
        "data": "eyJldmVudCI6ICJDV0wgQ09OVFJPTCBNRVNTQUdFOiBDaGVja2luZyBoZWFsdGggb2YgZGVzdGluYXRpb24gRmlyZWhvc2UuIiwgImhvc3QiOiAiYXJuOmF3czpmaXJlaG9zZTpldS13ZXN0LTI6MDkyNDIwMTU2ODAxOmRlbGl2ZXJ5c3RyZWFtL3Rlc3QtZmlyZWhvc2Utc3RyZWFtIiwgInNvdXJjZSI6ICJEZXN0aW5hdGlvbjoiLCAic291cmNldHlwZSI6ICJ0ZXN0OmF3czpjbG91ZHdhdGNoX2xvZ3MiLCAidGltZSI6ICIxNjI4NzU5MjQ0NzQxIn0=",
        "result": "Ok",
        "recordId": "49621017460761483038448697917559884585397934887094190082000001",
    }

    incoming_data_event = generate_data_message()
    actual_data = list(
        app_initialised.process_records(
            incoming_data_event["records"], incoming_data_event["deliveryStreamArn"]
        )
    )
    assert expected_record == actual_data[0]


def test_process_records_control_message(app_initialised):
    """Testing the processing of incoming records with control(test) message which gets dropped"""
    expected_data = {
        "result": "Dropped",
        "recordId": "49621017460761483038448697917559884585397934887094190082000000",
    }
    actual_data = list(
        app_initialised.process_records(
            INCOMING_CONTROL_EVENT["records"],
            INCOMING_CONTROL_EVENT["deliveryStreamArn"],
        )
    )
    assert expected_data == actual_data[0]


def test_transformation_event(app):
    """Testing the event message that gets created to be put into firehose stream"""
    data = {
        "messageType": "DATA_MESSAGE",
        "owner": "CloudwatchLogs",
        "logGroup": "",
        "logStream": "",
        "subscriptionFilters": ["Destination"],
        "logEvents": [
            {
                "id": "",
                "timestamp": 1628759244741,
                "message": "CWL CONTROL MESSAGE: Checking health of destination Firehose.",
            }
        ],
    }
    actual_data = app.transform_log_event(
        data["logEvents"][0],
        "arn:aws:firehose:eu-west-2:092420156801:deliverystream/test-firehose-stream",
        data["logGroup"],
        data["subscriptionFilters"][0],
    )

    assert (
        json.loads(actual_data)["host"]
        == "arn:aws:firehose:eu-west-2:092420156801:deliverystream/test-firehose-stream"
    )
    assert json.loads(actual_data)["sourcetype"] == "aws:cloudwatch_logs"
    assert (
        json.loads(actual_data)["event"]
        == "CWL CONTROL MESSAGE: Checking health of destination Firehose."
    )


def test_create_reingestion_record(app):
    actual_record = app.create_reingestion_record(generate_data_message()["records"][0])
    # "data" is a big blob of base64 encoded data, so just check it's there
    assert actual_record["data"] is not None


def test_get_reingestion_record(app):
    """Testing the reingestion of records in batch if size is more than limit"""
    actual_record = app.get_reingestion_record({"data": "test"})
    assert actual_record["Data"] == "test"


# Ignore moto warning that a mocked Splunk config will not work, this is fine as we just
#  care about testing putting the log onto Firehose, not that it gets to a mocked Splunk
@pytest.mark.filterwarnings(
    "ignore:A Splunk destination delivery stream is not yet implemented"
)
def test_record_to_stream(app, firehose, firehose_create):
    """Testing the putting of records into kinesis firehose stream"""
    test_data = [{"Data": "test"}]
    app.put_records_to_firehose_stream("test-stream", test_data, 4, 20)


def test_record_to_stream_fail(app, firehose):
    """Testing the failure behaviour of putting of record in firehose stream"""
    test_data = "INVLAID TEST DATA WHICH WILL CAUSE AN ERROR"
    with pytest.raises(RuntimeError) as context:
        app.put_records_to_firehose_stream("test-stream", test_data, 4, 20)
    assert "Could not put records after 20 attempts" in str(context)
