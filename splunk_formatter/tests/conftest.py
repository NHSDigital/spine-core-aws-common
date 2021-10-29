"""Splunk Log Formatter Test Config"""
# flake8: noqa: E501
# pylint: disable=line-too-long
import base64
import gzip
import io
import os

import boto3
import pytest
from moto import mock_firehose

from splunk_formatter.splunk_log_formatter import SplunkLogFormatter

INCOMING_CONTROL_EVENT = {
    "invocationId": "dcf4d11b-8d57-4b54-b40a-d66eb19fe197",
    "deliveryStreamArn": "arn:aws:firehose:eu-west-2:092420156801:deliverystream/test-firehose-stream",
    "region": "eu-west-2",
    "records": [
        {
            "recordId": "49621017460761483038448697917559884585397934887094190082000000",
            "approximateArrivalTimestamp": 1628759244804,
            "data": "H4sIAAAAAAAAADWOzQqCQBRGX2W4awkM+5tdhLaxhAxaRMSkN2dIZ2TutYjo3cOs5eE78J0XNEikKtw/WwQJq2y732XpeRPn+XIdQwDuYdH3S+268qG40KmrCAKoXbX2rmtBwkA5e1TNgNRdqPCmZeNsYmpGTyCPp68X39Fyjy8w5aCzaZBYNS3IcDqezyaLcRTNojD45/UBh1T88sQvT4qVxuJmbCU0qpq1cFdRIrGxqn8WifGoHeEI3qf3B50ewVvsAAAA",
        }
    ],
}


@pytest.fixture(scope="package", autouse=True)
def env_vars():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"

    os.environ["SPLUNK_SOURCE_TYPE_PREFIX"] = "test"
    # base64 data created in terraform from:
    #   base64gzip(jsonencode({"aws"="aws_test","audit"="audit_test","default"="app_test"}))
    os.environ[
        "SPLUNK_INDEXES_TO_LOGS_LEVELS"
    ] = "H4sIAPrJe2EAA6tWSixNySxRsoLQ8SWpxSVKOkqJ5cUgofJimEBKalpiaQ5YXUEBRLAWAOs/OcI8AAAA"


@pytest.fixture(scope="function")
def firehose():
    """A mocked Firehose client"""
    with mock_firehose():
        yield boto3.client("firehose", region_name="eu-west-2")


@pytest.fixture(scope="function")
def firehose_create(firehose):  # pylint: disable=redefined-outer-name
    """A mocked Firehose stream"""
    firehose.create_delivery_stream(
        DeliveryStreamName="test-stream",
        SplunkDestinationConfiguration={
            "HECEndpoint": "https://example.com/test",
            "HECEndpointType": "Event",
            "HECToken": "test-token",
            "S3Configuration": {
                "RoleARN": "test",
                "BucketARN": "test",
            },
        },
    )


@pytest.fixture(scope="function")
def app(firehose):  # pylint: disable=unused-argument,redefined-outer-name
    """A mocked Splunk Log Formatter class"""
    formatter = SplunkLogFormatter()
    formatter.initialise()
    return formatter


def generate_data_message():
    """Generates the input event for data message which gets zipped and base64 encoded just like real-time"""
    log = b'{"messageType":"DATA_MESSAGE","owner":"CloudwatchLogs","logGroup":"","logStream":"","subscriptionFilters":[ "Destination" ],"logEvents":[{"id":"","timestamp":1628759244741,"message":"CWL CONTROL MESSAGE: Checking health of destination Firehose."}]}'
    file = io.BytesIO()
    with gzip.GzipFile(fileobj=file, mode="wb") as gzip_file:
        gzip_file.write(log)
    enc_data = base64.encodebytes(file.getvalue())

    return {
        "invocationId": "dcf4d11b-8d57-4b54-b40a-d66eb19fe197",
        "deliveryStreamArn": "arn:aws:firehose:eu-west-2:092420156801:deliverystream/test-firehose-stream",
        "region": "eu-west-2",
        "records": [
            {
                "recordId": "49621017460761483038448697917559884585397934887094190082000001",
                "approximateArrivalTimestamp": 1628759244804,
                "data": enc_data,
                "kinesisRecordMetadata": {
                    "sequenceNumber": "49605230427854536169624763988300178155600757073314316306",
                    "subsequenceNumber": 0,
                    "partitionKey": "fadff67a-6803-4db5-8bed-4fcbcb0ed5db",
                    "shardId": "shardId-000000000001",
                    "approximateArrivalTimestamp": 1584514759230,
                },
            }
        ],
    }
