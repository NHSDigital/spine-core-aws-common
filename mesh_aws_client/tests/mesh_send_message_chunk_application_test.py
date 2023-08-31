""" Testing MeshSendMessageChunk Application """
import json
from http import HTTPStatus
from unittest import mock

import boto3
import requests_mock
from moto import mock_s3, mock_ssm

from mesh_aws_client.mesh_send_message_chunk_application import (
    MeshSendMessageChunkApplication,
    MaxByteExceededException,
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

    @mock_ssm
    @mock_s3
    @mock.patch.object(MeshSendMessageChunkApplication, "_create_new_internal_id")
    @requests_mock.Mocker()
    def test_mesh_send_file_chunk_app_no_chunks_happy_path(
        self, mock_create_new_internal_id, response_mocker
    ):
        """Test the lambda with small file, no chunking, happy path"""
        mock_create_new_internal_id.return_value = MeshTestingCommon.KNOWN_INTERNAL_ID

        response_mocker.get(
            "/messageexchange/MESH-TEST2",
            headers={
                "Content-Type": "application/json",
                "Content-Length": "44",
                "Connection": "keep-alive",
            },
        )
        response_mocker.get(
            "/messageexchange/MESH-TEST2/inbox",
            headers={
                "Content-Type": "application/json",
                "Connection": "keep-alive",
            },
            text=json.dumps(
                {
                    "messages": [
                        MeshTestingCommon.KNOWN_MESSAGE_ID1,
                        MeshTestingCommon.KNOWN_MESSAGE_ID2,
                        MeshTestingCommon.KNOWN_MESSAGE_ID3,
                    ]
                }
            ),
        )
        response_mocker.post(
            "/messageexchange/MESH-TEST2/outbox",
            text=json.dumps({"messageID": "20210711164906010267_97CCD9"}),
            headers={
                "Content-Type": "application/json",
                "Content-Length": "44",
                "Connection": "keep-alive",
            },
            request_headers={
                "mex-subject": "Custom Subject",
            },
        )
        s3_client = boto3.client("s3", config=MeshTestingCommon.aws_config)
        ssm_client = boto3.client("ssm", config=MeshTestingCommon.aws_config)
        MeshTestingCommon.setup_mock_aws_s3_buckets(self.environment, s3_client)
        MeshTestingCommon.setup_mock_aws_ssm_parameter_store(
            self.environment, ssm_client
        )
        mock_lambda_input = self._sample_single_chunk_input_event()
        expected_lambda_response = self._sample_single_chunk_input_event()
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
        self.assertTrue(
            self.log_helper.was_value_logged("MESHSEND0008", "Log_Level", "INFO")
        )

    # pylint: disable=too-many-locals
    @mock_ssm
    @mock_s3
    @mock.patch.object(MeshSendMessageChunkApplication, "_create_new_internal_id")
    @requests_mock.Mocker()
    def test_mesh_send_file_chunk_app_2_chunks_happy_path(
        self,
        mock_create_new_internal_id,
        response_mocker,
    ):
        """Test the lambda with small file, in 4 chunks, happy path"""
        mock_create_new_internal_id.return_value = MeshTestingCommon.KNOWN_INTERNAL_ID

        response_mocker.get(
            "/messageexchange/MESH-TEST2",
            headers={
                "Content-Type": "application/json",
                "Connection": "keep-alive",
            },
            text="",
        )
        response_mocker.get(
            "/messageexchange/MESH-TEST2/inbox",
            headers={
                "Content-Type": "application/json",
                "Connection": "keep-alive",
            },
            text=json.dumps(
                {
                    "messages": [
                        MeshTestingCommon.KNOWN_MESSAGE_ID1,
                        MeshTestingCommon.KNOWN_MESSAGE_ID2,
                        MeshTestingCommon.KNOWN_MESSAGE_ID3,
                    ]
                }
            ),
        )
        custom_request_headers = {
            "mex-subject": "Custom Subject",
        }
        response_mocker.post(
            "/messageexchange/MESH-TEST2/outbox",
            text=json.dumps({"messageID": "20210711164906010267_97CCD9"}),
            headers={
                "Content-Type": "application/json",
                "Content-Length": "33",
                "Connection": "keep-alive",
            },
            request_headers=custom_request_headers,
        )
        response_mocker.post(
            "/messageexchange/MESH-TEST2/outbox/20210711164906010267_97CCD9/2",
            text=json.dumps({"messageID": "20210711164906010267_97CCD9"}),
            headers={
                "Content-Type": "application/json",
                "Content-Length": "33",
                "Connection": "keep-alive",
            },
            request_headers=custom_request_headers,
        )
        response_mocker.post(
            "/messageexchange/MESH-TEST2/outbox/20210711164906010267_97CCD9/3",
            text=json.dumps({"messageID": "20210711164906010267_97CCD9"}),
            headers={
                "Content-Type": "application/json",
                "Content-Length": "33",
                "Connection": "keep-alive",
            },
            request_headers=custom_request_headers,
        )
        response_mocker.post(
            "/messageexchange/MESH-TEST2/outbox/20210711164906010267_97CCD9/4",
            text=json.dumps({"messageID": "20210711164906010267_97CCD9"}),
            headers={
                "Content-Type": "application/json",
                "Content-Length": "33",
                "Connection": "keep-alive",
            },
            request_headers=custom_request_headers,
        )
        s3_client = boto3.client("s3", config=MeshTestingCommon.aws_config)
        ssm_client = boto3.client("ssm", config=MeshTestingCommon.aws_config)
        MeshTestingCommon.setup_mock_aws_s3_buckets(self.environment, s3_client)
        MeshTestingCommon.setup_mock_aws_ssm_parameter_store(
            self.environment, ssm_client
        )
        mock_input = self._sample_multi_chunk_input_event()
        mock_response = self._sample_multi_chunk_input_event()
        mock_response["body"].update({"complete": True})
        mock_response["body"].update({"will_compress": True})
        mock_response["body"].update({"chunk_number": 4})

        count = 1
        while not mock_input["body"]["complete"]:
            chunk_number = mock_input["body"].get("chunk_number", 1)
            print(f">>>>>>>>>>> Chunk {chunk_number} >>>>>>>>>>>>>>>>>>>>")
            try:
                response = self.app.main(
                    event=mock_input, context=MeshTestingCommon.CONTEXT
                )
            except Exception as exception:  # pylint: disable=broad-except
                # need to fail happy pass on any exception
                self.fail(f"Invocation crashed with Exception {str(exception)}")
            if count == 1:
                message_id = response["body"]["message_id"]
            count = count + 1
            mock_input = response
            print(response)

        mock_response["body"]["message_id"] = message_id
        self.assertDictEqual(mock_response, response)

        # Check completion
        self.assertTrue(
            self.log_helper.was_value_logged("LAMBDA0003", "Log_Level", "INFO")
        )
        self.assertTrue(
            self.log_helper.was_value_logged("MESHSEND0008", "Log_Level", "INFO")
        )

    @mock_ssm
    @mock_s3
    @mock.patch.object(MeshSendMessageChunkApplication, "_create_new_internal_id")
    @requests_mock.Mocker()
    def test_mesh_send_file_chunk_app_too_many_chunks(
        self, mock_create_new_internal_id, fake_mesh_server
    ):
        """Test lambda throws MaxByteExceededException when too many chunks specified"""
        mock_create_new_internal_id.return_value = MeshTestingCommon.KNOWN_INTERNAL_ID

        fake_mesh_server.get(
            "/messageexchange/MESH-TEST2",
            headers={
                "Content-Type": "application/json",
                "Connection": "keep-alive",
            },
            text="",
        )
        fake_mesh_server.get(
            "/messageexchange/MESH-TEST2/inbox",
            headers={
                "Content-Type": "application/json",
                "Connection": "keep-alive",
            },
            text=json.dumps(
                {
                    "messages": [
                        MeshTestingCommon.KNOWN_MESSAGE_ID1,
                        MeshTestingCommon.KNOWN_MESSAGE_ID2,
                        MeshTestingCommon.KNOWN_MESSAGE_ID3,
                    ]
                }
            ),
        )
        fake_mesh_server.post(
            "/messageexchange/MESH-TEST2/outbox",
            text=json.dumps({"messageID": "20210711164906010267_97CCD9"}),
            headers={
                "Content-Type": "application/json",
                "Content-Length": "33",
                "Connection": "keep-alive",
            },
        )

        s3_client = boto3.client("s3", config=MeshTestingCommon.aws_config)
        ssm_client = boto3.client("ssm", config=MeshTestingCommon.aws_config)
        MeshTestingCommon.setup_mock_aws_s3_buckets(self.environment, s3_client)
        MeshTestingCommon.setup_mock_aws_ssm_parameter_store(
            self.environment, ssm_client
        )
        mock_input = self._sample_too_many_chunks_input_event()
        mock_response = self._sample_too_many_chunks_input_event()
        mock_response["body"].update({"complete": True})
        mock_response["body"].update({"will_compress": True})

        with self.assertRaises(MaxByteExceededException) as context:
            self.app.main(event=mock_input, context=MeshTestingCommon.CONTEXT)
        self.assertIsInstance(context.exception, MaxByteExceededException)

    def _sample_single_chunk_input_event(self):
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
                "compress_ratio": 1,
                "will_compress": False,
            },
        }

    def _sample_multi_chunk_input_event(self):
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
                "total_chunks": 4,
                "chunk_size": 10,
                "complete": False,
                "current_byte_position": 0,
                "compress_ratio": 1,
                "will_compress": False,
            },
        }

    def _sample_too_many_chunks_input_event(self):
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
                "total_chunks": 2,
                "chunk_size": 10,
                "complete": False,
                "current_byte_position": 33,
                "compress_ratio": 1,
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
