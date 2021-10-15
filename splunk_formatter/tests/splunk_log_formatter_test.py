import base64
import gzip
import io
import json
import os
import pytest
from unittest import TestCase

import boto3
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

ENV_VARS = {
    "SPLUNK_SOURCE_TYPE_PREFIX": "test",
    # base64 data created in terraform from:
    #   base64encode(jsonencode({"aws"="aws_test","audit"="audit_test","default"="app_test"}))
    "SPLUNK_INDEXES_TO_LOGS_LEVELS": "eyJhdWRpdCI6ImF1ZGl0X3Rlc3QiLCJhd3MiOiJhd3NfdGVzdCIsImRlZmF1bHQiOiJhcHBfdGVzdCJ9",
}

# This is suppresses "UserWarning: A Splunk destination delivery stream is not yet implemented"
@pytest.mark.filterwarnings("ignore::UserWarning")
class TestSplunkLogFormatter(TestCase):
    mock_firehose = mock_firehose()

    def setUp(self):
        """Common setup for all tests"""
        self.maxDiff = None

        os.environ["SPLUNK_SOURCE_TYPE_PREFIX"] = ENV_VARS["SPLUNK_SOURCE_TYPE_PREFIX"]
        os.environ["SPLUNK_INDEXES_TO_LOGS_LEVELS"] = ENV_VARS[
            "SPLUNK_INDEXES_TO_LOGS_LEVELS"
        ]

        self.mock_firehose.start()

        self.app = SplunkLogFormatter()
        self.app.initialise()

        firehose = boto3.client("firehose")
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

    def tearDown(self):
        self.mock_firehose.stop()

    def test_get_source_type_default(self):
        given_log_group = "UploaderLambdaLogs"
        given_prefix = "test"
        expected = "test:aws:cloudwatch_logs"

        source_type = self.app.get_source_type(given_log_group, given_prefix)
        self.assertEqual(source_type, expected)

    def test_get_source_type_no_prefix(self):
        given_log_group = "UploaderLambdaLogs"
        given_prefix = None
        expected = "aws:cloudwatch_logs"

        source_type = self.app.get_source_type(given_log_group, given_prefix)
        self.assertEqual(source_type, expected)

    def test_get_source_type_cloudtrail(self):
        given_log_group = "MainCloudTrailLogs"
        given_prefix = "test"
        expected = "test:aws:cloudtrail"

        source_type = self.app.get_source_type(given_log_group, given_prefix)
        self.assertEqual(source_type, expected)

    def test_get_source_type_vpc(self):
        given_log_group = "MainVPCLogs"
        given_prefix = "test"
        expected = "test:aws:cloudwatch_logs:vpcflow"

        source_type = self.app.get_source_type(given_log_group, given_prefix)
        self.assertEqual(source_type, expected)

    def test_get_splunk_indexes_to_logs_levels(self):
        given = ENV_VARS["SPLUNK_INDEXES_TO_LOGS_LEVELS"]
        expected = {"aws": "aws_test", "audit": "audit_test", "default": "app_test"}

        mappings = self.app.get_splunk_indexes_to_logs_levels(given)
        self.assertEqual(mappings, expected)

    def test_get_index_audit(self):
        given_log_level = "AUDIT"
        given_index_mappings = {
            "aws": "aws_test",
            "audit": "audit_test",
            "default": "app_test",
        }
        expected = "audit_test"

        index = self.app.get_index(given_log_level, given_index_mappings)
        self.assertEqual(index, expected)

    def test_get_index_unknown(self):
        given_log_level = "UNKNOWN"
        given_index_mappings = {
            "aws": "aws_test",
            "audit": "audit_test",
            "default": "app_test",
        }
        expected = "app_test"

        index = self.app.get_index(given_log_level, given_index_mappings)
        self.assertEqual(index, expected)

    def test_get_level_of_log_info(self):
        given = "15/10/2021 14:10:13.692 Log_Level=INFO Process=test-lr_02_validate_and_parse internalID=20211015141013691760_0CF842 logReference=LR02I01 - Something has happened"
        expected = "INFO"

        level = self.app.get_level_of_log(given)
        self.assertEqual(level, expected)

    def test_get_level_of_log_warning(self):
        given = "15/10/2021 14:10:13.692 Log_Level=WARNING Process=test-lr_02_validate_and_parse internalID=20211015141013691760_0CF842 logReference=LAMBDA9999 - Probably not a good thing"
        expected = "WARNING"

        level = self.app.get_level_of_log(given)
        self.assertEqual(level, expected)

    def test_get_level_of_log_critical(self):
        given = "15/10/2021 14:10:13.692 Log_Level=CRITICAL Process=test-lr_02_validate_and_parse internalID=20211015141013691760_0CF842 logReference=LAMBDA9999 - Big error"
        expected = "CRITICAL"

        level = self.app.get_level_of_log(given)
        self.assertEqual(level, expected)

    def test_get_level_of_log_audit(self):
        given = "15/10/2021 14:10:13.692 Log_Level=AUDIT Process=test-lr_02_validate_and_parse internalID=20211015141013691760_0CF842 logReference=LAMBDA9999 - This is a sensitive log line"
        expected = "AUDIT"

        level = self.app.get_level_of_log(given)
        self.assertEqual(level, expected)

    def test_get_level_of_log_aws(self):
        given = "REPORT RequestId: 97c94011-4400-406e-abb4-343cc9d4d22b Duration: 2.07 ms Billed Duration: 3 ms Memory Size: 128 MB Max Memory Used: 75 MB"
        expected = "AWS"

        level = self.app.get_level_of_log(given)
        self.assertEqual(level, expected)

    def test_get_level_of_log_unknown(self):
        given = "15/10/2021 14:10:13.692 Log_Level=OMG Process=test-lr_02_validate_and_parse internalID=20211015141013691760_0CF842 logReference=LAMBDA9999 - This is a suprising log line"
        expected = "UNKNOWN"

        level = self.app.get_level_of_log(given)
        self.assertEqual(level, expected)

    def test_get_level_of_log_malformed(self):
        given = "Well this should probably not be a log line"
        expected = "UNKNOWN"

        level = self.app.get_level_of_log(given)
        self.assertEqual(level, expected)

    def test_process_records_control_message(self):
        """Testing the processing of incoming records with control(test) message which gets dropped"""
        expected_data = {
            "result": "Dropped",
            "recordId": "49621017460761483038448697917559884585397934887094190082000000",
        }
        actual_data = list(
            self.app.process_records(
                INCOMING_CONTROL_EVENT["records"],
                INCOMING_CONTROL_EVENT["deliveryStreamArn"],
            )
        )
        self.assertEqual(expected_data, actual_data[0])

    def test_cw_logs_data_message_input(self):
        """Testing the processing of incoming records with actual data message which gets accepted"""
        expected_record = {
            "data": "eyJldmVudCI6ICJDV0wgQ09OVFJPTCBNRVNTQUdFOiBDaGVja2luZyBoZWFsdGggb2YgZGVzdGluYXRpb24gRmlyZWhvc2UuIiwgImhvc3QiOiAiYXJuOmF3czpmaXJlaG9zZTpldS13ZXN0LTI6MDkyNDIwMTU2ODAxOmRlbGl2ZXJ5c3RyZWFtL3Rlc3QtZmlyZWhvc2Utc3RyZWFtIiwgImluZGV4IjogImFwcF90ZXN0IiwgInNvdXJjZSI6ICJEZXN0aW5hdGlvbjoiLCAic291cmNldHlwZSI6ICJ0ZXN0OmF3czpjbG91ZHdhdGNoX2xvZ3MiLCAidGltZSI6ICIxNjI4NzU5MjQ0NzQxIn0=",
            "result": "Ok",
            "recordId": "49621017460761483038448697917559884585397934887094190082000001",
        }

        INCOMING_DATA_EVENT = self._generate_data_message()
        actual_data = list(
            self.app.process_records(
                INCOMING_DATA_EVENT["records"], INCOMING_DATA_EVENT["deliveryStreamArn"]
            )
        )
        self.assertEqual(expected_record, actual_data[0])

    def test_transformation_event(self):
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
        actual_data = self.app.transform_log_event(
            data["logEvents"][0],
            "arn:aws:firehose:eu-west-2:092420156801:deliverystream/test-firehose-stream",
            data["logGroup"],
            data["subscriptionFilters"][0],
        )

        self.assertEqual(
            json.loads(actual_data)["host"],
            "arn:aws:firehose:eu-west-2:092420156801:deliverystream/test-firehose-stream",
        )
        self.assertEqual(
            json.loads(actual_data)["sourcetype"], "test:aws:cloudwatch_logs"
        )
        self.assertEqual(json.loads(actual_data)["index"], "app_test")
        self.assertEqual(
            json.loads(actual_data)["event"],
            "CWL CONTROL MESSAGE: Checking health of destination Firehose.",
        )

    def test_create_reingestion_record(self):
        actual_record = self.app.create_reingestion_record(
            self._generate_data_message()["records"][0]
        )
        # "data" is a big blob of base64 encoded data, so just check it's there
        self.assertIsNotNone(actual_record["data"])

    def test_get_reingestion_record(self):
        """Testing the reingestion of records in batch if size is more than limit"""
        actual_record = self.app.get_reingestion_record({"data": "test"})
        self.assertEqual(actual_record["Data"], "test")

    def test_record_to_stream(self):
        """Testing the putting of records into kinesis firehose stream on localstack"""
        test_data = [{"Data": "test"}]
        self.app.put_records_to_firehose_stream("test-stream", test_data, 4, 20)

    def test_record_to_stream_fail(self):
        """Testing the failure behaviour of putting of record in firehose stream on localstack"""
        test_data = "INVLAID TEST DATA WHICH WILL CAUSE AN ERROR"
        with self.assertRaises(RuntimeError) as context:
            self.app.put_records_to_firehose_stream("test-stream", test_data, 4, 20)
        self.assertTrue(
            "Could not put records after 20 attempts" in str(context.exception)
        )

    @staticmethod
    def _generate_data_message():
        """Generates the input event for data message which gets zipped and base64 encoded just like real-time"""
        st = b'{"messageType":"DATA_MESSAGE","owner":"CloudwatchLogs","logGroup":"","logStream":"","subscriptionFilters":[ "Destination" ],"logEvents":[{"id":"","timestamp":1628759244741,"message":"CWL CONTROL MESSAGE: Checking health of destination Firehose."}]}'
        fo = io.BytesIO()
        with gzip.GzipFile(fileobj=fo, mode="wb") as f:
            f.write(st)
        enc_data = base64.encodebytes(fo.getvalue())

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
