import base64
import gzip
import io
import json
import os
from unittest import TestCase, mock

import boto3
from botocore.stub import Stubber

from splunk_formatter.splunk_log_formatter import SplunkLogFormatter, lambda_handler

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

ENV_VARS = {"DEFAULT_INDEX_PREFIX": "app", "ENV": "dev"}


class TestSplunkLogFormatter(TestCase):
    def setUp(self):
        """Common setup for all tests"""
        self.app = SplunkLogFormatter()

    def test_get_source_type_default(self):
        given_log_group = "UploaderLambdaLogs"
        given_default_source_type = "default"

        expected = "default"

        source_type = self.app.get_source_type(
            given_log_group, given_default_source_type
        )

        self.assertEqual(source_type, expected)

    def test_get_source_type_cloudtrail(self):
        given_log_group = "MainCloudTrailLogs"
        given_default_source_type = "default"

        expected = "aws:cloudtrail"

        source_type = self.app.get_source_type(
            given_log_group, given_default_source_type
        )

        self.assertEqual(source_type, expected)

    def test_get_source_type_vpc(self):
        given_log_group = "MainVPCLogs"
        given_default_source_type = "default"

        expected = "aws:cloudwatchlogs:vpcflow"

        source_type = self.app.get_source_type(
            given_log_group, given_default_source_type
        )

        self.assertEqual(source_type, expected)

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

    @mock.patch.dict(os.environ, ENV_VARS)
    def test_cw_logs_data_message_input(self):
        """Testing the processing of incoming records with actual data message which gets accepted"""
        expected_record = {
            "data": "eyJ0aW1lIjogMTYyODc1OTI0NDc0MSwiaG9zdCI6ICJhcm46YXdzOmZpcmVob3NlOmV1LXdlc3QtMjowOTI0MjAxNTY4MDE6ZGVsaXZlcnlzdHJlYW0vdGVzdC1maXJlaG9zZS1zdHJlYW0iLCJzb3VyY2UiOiAiRGVzdGluYXRpb246Iiwic291cmNldHlwZSI6ImF3czpjbG91ZHdhdGNoIiwiaW5kZXgiOiJsYW1iZGFfZ3BfcmVnX2RldiIsImV2ZW50IjogIkNXTCBDT05UUk9MIE1FU1NBR0U6IENoZWNraW5nIGhlYWx0aCBvZiBkZXN0aW5hdGlvbiBGaXJlaG9zZS4ifQoK",
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

    @mock.patch.dict(os.environ, ENV_VARS)
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
        self.assertEqual(json.loads(actual_data)["sourcetype"], "aws:cloudwatch")
        self.assertEqual(json.loads(actual_data)["index"], "app_gp_reg_dev")
        self.assertEqual(
            json.loads(actual_data)["event"],
            "CWL CONTROL MESSAGE: Checking health of destination Firehose.",
        )

    def test_create_reingestion_record(self):
        """Testing the reingestion record creation which has data and partition key"""
        actual_record = self.app.create_reingestion_record(
            True, self._generate_data_message()["records"][0]
        )
        self.assertEqual(
            actual_record["partitionKey"], "fadff67a-6803-4db5-8bed-4fcbcb0ed5db"
        )

    def test_get_reingestion_record(self):
        """Testing the reingestion of records in batch if size is more than limit"""
        actual_record = self.app.get_reingestion_record(
            True, {"data": "test", "partitionKey": "key"}
        )
        self.assertEqual(actual_record["PartitionKey"], "key")

    # def test_record_to_stream(self):
    #     """Testing the putting of records into kinesis firehose stream on localstack"""
    #     client = boto3.client(
    #         "firehose", region_name="eu-west-2", endpoint_url="http://localhost:4566"
    #     )
    #     test_data = [{"Data": "test"}]
    #     self.app.put_records_to_firehose_stream(
    #         "local-gp-reg-lambda-kinesis-firehose-to-splunk-stream",
    #         test_data,
    #         client,
    #         4,
    #         20,
    #     )

    # def test_record_to_stream_fail(self):
    #     """Testing the failure behaviour of putting of record in firehose stream on localstack"""
    #     client = boto3.client(
    #         "firehose", region_name="eu-west-2", endpoint_url="http://localhost:4566"
    #     )
    #     test_data = [{"Data": "test"}]
    #     stubber = Stubber(client)
    #     stubber.add_client_error("put_record_batch")
    #     stubber.activate()
    #     with self.assertRaises(RuntimeError) as context:
    #         self.app.put_records_to_firehose_stream(
    #             "local-gp-reg-lambda-kinesis-firehose-to-splunk-stream",
    #             test_data,
    #             client,
    #             4,
    #             20,
    #         )
    #     self.assertTrue(
    #         "Could not put records after 20 attempts" in str(context.exception)
    #     )

    @mock.patch.dict(os.environ, ENV_VARS)
    def test_lambda_handler(self):
        """Testing the overall lambda_handler method record response"""
        expected_record_to_stream = {
            "records": [
                {
                    "data": "eyJ0aW1lIjogMTYyODc1OTI0NDc0MSwiaG9zdCI6ICJhcm46YXdzOmZpcmVob3NlOmV1LXdlc3QtMjowOTI0MjAxNTY4MDE6ZGVsaXZlcnlzdHJlYW0vdGVzdC1maXJlaG9zZS1zdHJlYW0iLCJzb3VyY2UiOiAiRGVzdGluYXRpb246Iiwic291cmNldHlwZSI6ImF3czpjbG91ZHdhdGNoIiwiaW5kZXgiOiJsYW1iZGFfZ3BfcmVnX2RldiIsImV2ZW50IjogIkNXTCBDT05UUk9MIE1FU1NBR0U6IENoZWNraW5nIGhlYWx0aCBvZiBkZXN0aW5hdGlvbiBGaXJlaG9zZS4ifQoK",
                    "result": "Ok",
                    "recordId": "49621017460761483038448697917559884585397934887094190082000001",
                }
            ]
        }
        actual_record_to_stream = lambda_handler(self._generate_data_message(), "")
        self.assertEqual(actual_record_to_stream, expected_record_to_stream)

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
