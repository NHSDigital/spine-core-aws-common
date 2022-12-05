""" Testing MeshSendMessageChunk Application """
from http import HTTPStatus
from unittest import mock
import json

from moto import mock_s3, mock_ssm, mock_secretsmanager
import boto3
import requests_mock

from mesh_aws_client.mesh_send_message_chunk_application import (
    MeshSendMessageChunkApplication,
)
from mesh_aws_client.tests.mesh_testing_common import (
    MeshTestCase,
    MeshTestingCommon,
)


class TestMeshSendMessageChunkApplication(MeshTestCase):
    """Testing MeshSendMessageChunk application"""

    FILE_CONTENT = "123456789012345678901234567890123"
    FILE_SIZE = len(FILE_CONTENT)

    MEBIBYTE = 1024 * 1024
    DEFAULT_BUFFER_SIZE = 20 * MEBIBYTE

    @mock.patch.dict("os.environ", MeshTestingCommon.os_environ_values)
    def setUp(self):
        """Override setup to use correct application object"""
        super().setUp()
        self.app = MeshSendMessageChunkApplication()
        self.environment = self.app.system_config["Environment"]

    @mock_secretsmanager
    @mock_ssm
    @mock_s3
    @mock.patch.object(MeshSendMessageChunkApplication, "_create_new_internal_id")
    @requests_mock.Mocker()
    def test_mesh_send_file_single_chunk_no_parts(
        self, mock_create_new_internal_id, response_mocker
    ):
        """Test the lambda with small file, no chunking, happy path"""
        mock_create_new_internal_id.return_value = MeshTestingCommon.KNOWN_INTERNAL_ID
        response_mocker.post(
            "/messageexchange/MESH-TEST2/outbox",
            text=json.dumps({"messageID": "20210711164906010267_97CCD9"}),
            headers={
                "Content-Type": "application/json",
                "Content-Length": "44",
                "Connection": "keep-alive",
            },
        )
        response_mocker.get(
            "/messageexchange/MESH-TEST2/inbox",
            text=json.dumps({"messages": []}),
            headers={
                "Content-Type": "application/json",
                "Content-Length": "10",
                "Connection": "keep-alive",
            },
        )
        s3_client = boto3.client("s3", config=MeshTestingCommon.aws_config)
        ssm_client = boto3.client("ssm", config=MeshTestingCommon.aws_config)
        MeshTestingCommon.setup_mock_aws_s3_buckets(self.environment, s3_client)
        MeshTestingCommon.setup_mock_aws_ssm_parameter_store(
            self.environment, ssm_client
        )
        mock_lambda_input = self._sample_input_event()
        expected_lambda_response = self._sample_input_event()
        expected_lambda_response["body"].update({"complete": True})

        try:
            lambda_response = self.app.main(
                event=mock_lambda_input, context=MeshTestingCommon.CONTEXT
            )
        except Exception as e:  # pylint: disable=broad-except
            # need to fail happy pass on any exception
            self.fail(f"Invocation crashed with Exception {str(e)}")

        lambda_response["body"].pop("message_id")
        self.assertDictEqual(expected_lambda_response, lambda_response)
        # Check completion
        self.assertTrue(
            self.log_helper.was_value_logged("LAMBDA0003", "Log_Level", "INFO")
        )

    # pylint: disable=too-many-locals
    @mock_secretsmanager
    @mock_ssm
    @mock_s3
    @mock.patch.object(MeshSendMessageChunkApplication, "_create_new_internal_id")
    @requests_mock.Mocker()
    def test_mesh_send_file_multi_chunk_no_parts(
        self, mock_create_new_internal_id, response_mocker
    ):
        """
        Test the lambda with small file in 3 chunks, happy path
        Note that current byte won't be correct because of mocking.
        """
        # FILE_CONTENT = "123456789012345678901234567890123"
        mock_create_new_internal_id.return_value = MeshTestingCommon.KNOWN_INTERNAL_ID
        message_id = "20210711164906010267_97CCD9"
        response_mocker.post(
            "/messageexchange/MESH-TEST2/outbox",
            text=json.dumps({"messageID": message_id}),
            headers={
                "Content-Type": "application/json",
                "Content-Length": "44",
                "Connection": "keep-alive",
            },
        )
        response_mocker.get(
            "/messageexchange/MESH-TEST2/inbox",
            text=json.dumps({"messages": []}),
            headers={
                "Content-Type": "application/json",
                "Content-Length": "10",
                "Connection": "keep-alive",
            },
        )

        s3_client = boto3.client("s3", config=MeshTestingCommon.aws_config)
        ssm_client = boto3.client("ssm", config=MeshTestingCommon.aws_config)
        MeshTestingCommon.setup_mock_aws_s3_buckets(self.environment, s3_client)
        MeshTestingCommon.setup_mock_aws_ssm_parameter_store(
            self.environment, ssm_client
        )
        lambda_input_1 = self._sample_input_event_multi_chunk()
        expected_lambda_response_1 = self._sample_input_event_multi_chunk()
        expected_lambda_response_1["body"].update({"message_id": message_id})
        expected_lambda_response_1["body"].update({"chunk_number": 2})

        try:
            lambda_response_1 = self.app.main(
                event=lambda_input_1, context=MeshTestingCommon.CONTEXT
            )
        except Exception as e:  # pylint: disable=broad-except
            # need to fail happy pass on any exception
            self.fail(f"Invocation crashed with Exception {str(e)}")

        self.assertDictEqual(expected_lambda_response_1, lambda_response_1)
        self.assertTrue(
            self.log_helper.was_value_logged("LAMBDA0003", "Log_Level", "INFO")
        )

        # 2nd Chunk
        response_mocker.post(
            f"/messageexchange/MESH-TEST2/outbox/{message_id}/2",
            text=json.dumps({"messageID": message_id}),
            headers={
                "Content-Type": "application/json",
                "Content-Length": "44",
                "Connection": "keep-alive",
            },
        )
        lambda_input_2 = lambda_response_1
        expected_lambda_response_2 = self._sample_input_event_multi_chunk()
        expected_lambda_response_2["body"].update({"message_id": message_id})
        expected_lambda_response_2["body"].update({"chunk_number": 3})

        try:
            lambda_response_2 = self.app.main(
                event=lambda_input_2, context=MeshTestingCommon.CONTEXT
            )
        except Exception as e:  # pylint: disable=broad-except
            # need to fail happy pass on any exception
            self.fail(f"Invocation crashed with Exception {str(e)}")

        self.assertDictEqual(expected_lambda_response_2, lambda_response_2)
        self.assertTrue(
            self.log_helper.was_value_logged("LAMBDA0003", "Log_Level", "INFO")
        )

        # 3rd and final Chunk
        response_mocker.post(
            f"/messageexchange/MESH-TEST2/outbox/{message_id}/3",
            text=json.dumps({"messageID": message_id}),
            headers={
                "Content-Type": "application/json",
                "Content-Length": "44",
                "Connection": "keep-alive",
            },
        )
        lambda_input_3 = lambda_response_2
        expected_lambda_response_3 = self._sample_input_event_multi_chunk()
        expected_lambda_response_3["body"].update({"message_id": message_id})
        expected_lambda_response_3["body"].update({"chunk_number": 3})
        expected_lambda_response_3["body"].update({"complete": True})

        try:
            lambda_response_3 = self.app.main(
                event=lambda_input_3, context=MeshTestingCommon.CONTEXT
            )
        except Exception as e:  # pylint: disable=broad-except
            # need to fail happy pass on any exception
            self.fail(f"Invocation crashed with Exception {str(e)}")

        self.assertDictEqual(expected_lambda_response_3, lambda_response_3)
        self.assertTrue(
            self.log_helper.was_value_logged("LAMBDA0003", "Log_Level", "INFO")
        )

    # pylint: enable=too-many-locals

    def _sample_input_event(self):
        """Return Example input event"""
        return {
            "statusCode": HTTPStatus.OK.value,
            "headers": {"Content-Type": "application/json"},
            "body": {
                "internal_id": MeshTestingCommon.KNOWN_INTERNAL_ID,
                "src_mailbox": "MESH-TEST2",
                "dest_mailbox": "MESH-TEST1",
                "workflow_id": "TESTWORKFLOW",
                "bucket": f"{self.environment}-mesh",
                "key": "MESH-TEST2/outbound/testfile.json",
                "chunked": False,
                "chunk_number": 1,
                "total_chunks": 1,
                "chunk_size": 50,
                "complete": False,
                "current_byte_position": 0,
                "will_compress": False,
            },
        }

    def _sample_input_event_multi_chunk(self):
        """Return Example input event"""
        return {
            "statusCode": HTTPStatus.OK.value,
            "headers": {"Content-Type": "application/json"},
            "body": {
                "internal_id": MeshTestingCommon.KNOWN_INTERNAL_ID,
                "src_mailbox": "MESH-TEST2",
                "dest_mailbox": "MESH-TEST1",
                "workflow_id": "TESTWORKFLOW",
                "bucket": f"{self.environment}-mesh",
                "key": "MESH-TEST2/outbound/testfile.json",
                "chunked": True,
                "chunk_number": 1,
                "total_chunks": 3,
                "chunk_size": 14,
                "complete": False,
                "current_byte_position": 0,
                "will_compress": False,
            },
        }
