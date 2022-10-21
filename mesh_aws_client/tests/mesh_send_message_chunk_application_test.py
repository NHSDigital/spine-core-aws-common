""" Testing MeshSendMessageChunk Application """
from http import HTTPStatus
from unittest import mock
import json

from moto import mock_s3, mock_ssm
import boto3
import requests_mock

from mesh_aws_client.mesh_send_message_chunk_application import (
    MeshSendMessageChunkApplication, MaxByteExceededException,
)
from mesh_aws_client.tests.mesh_testing_common import (
    MeshTestCase,
    MeshTestingCommon,
)


class TestMeshSendMessageChunkApplication(MeshTestCase):
    """Testing MeshSendMessageChunk application"""

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
        self, mock_create_new_internal_id, fake_mesh_server
    ):
        """Test the lambda with small file, no chunking, happy path"""
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
        mock_input = self._sample_single_chunk_input_event()
        mock_response = self._sample_single_chunk_input_event()
        mock_response["body"].update({"complete": True})

        try:
            response = self.app.main(
                event=mock_input, context=MeshTestingCommon.CONTEXT
            )
        except Exception as e:  # pylint: disable=broad-except
            # need to fail happy pass on any exception
            self.fail(f"Invocation crashed with Exception {str(e)}")

        # Can't test like this with chunking!
        # self.assertEqual(self.app.body, MeshTestingCommon.FILE_CONTENT.encode("utf8"))

        response["body"].pop("message_id")
        self.assertDictEqual(mock_response, response)
        # Check completion
        self.assertTrue(
            self.log_helper.was_value_logged("LAMBDA0003", "Log_Level", "INFO")
        )

    @mock_ssm
    @mock_s3
    @mock.patch.object(MeshSendMessageChunkApplication, "_create_new_internal_id")
    @requests_mock.Mocker()
    def test_mesh_send_file_chunk_app_multi_chunk_happy_path(
        self, mock_create_new_internal_id, fake_mesh_server
    ):
        """Test the lambda with small file, in 4 chunks, happy path"""
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
        fake_mesh_server.post(
            "/messageexchange/MESH-TEST2/outbox/20210711164906010267_97CCD9/2",
            text=json.dumps({"messageID": "20210711164906010267_97CCD9"}),
            headers={
                "Content-Type": "application/json",
                "Content-Length": "33",
                "Connection": "keep-alive",
            },
        )
        fake_mesh_server.post(
            "/messageexchange/MESH-TEST2/outbox/20210711164906010267_97CCD9/3",
            text=json.dumps({"messageID": "20210711164906010267_97CCD9"}),
            headers={
                "Content-Type": "application/json",
                "Content-Length": "33",
                "Connection": "keep-alive",
            },
        )
        fake_mesh_server.post(
            "/messageexchange/MESH-TEST2/outbox/20210711164906010267_97CCD9/4",
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
                message_id = response['body']['message_id']
            count = count + 1
            mock_input = response
            print(response)

        # Can't test like this with chunking!
        # self.assertEqual(self.app.body, MeshTestingCommon.FILE_CONTENT.encode("utf8"))

        response["body"].pop("message_id")
        self.assertDictEqual(mock_response, response)

        # Check completion
        self.assertTrue(
            self.log_helper.was_value_logged("LAMBDA0003", "Log_Level", "INFO")
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
        fake_mesh_server.post(
            "/messageexchange/MESH-TEST2/outbox/20210711164906010267_97CCD9/2",
            text=json.dumps({"messageID": "20210711164906010267_97CCD9"}),
            headers={
                "Content-Type": "application/json",
                "Content-Length": "33",
                "Connection": "keep-alive",
            },
        )
        fake_mesh_server.post(
            "/messageexchange/MESH-TEST2/outbox/20210711164906010267_97CCD9/3",
            text=json.dumps({"messageID": "20210711164906010267_97CCD9"}),
            headers={
                "Content-Type": "application/json",
                "Content-Length": "33",
                "Connection": "keep-alive",
            },
        )
        fake_mesh_server.post(
            "/messageexchange/MESH-TEST2/outbox/20210711164906010267_97CCD9/4",
            text=json.dumps({"messageID": "20210711164906010267_97CCD9"}),
            headers={
                "Content-Type": "application/json",
                "Content-Length": "33",
                "Connection": "keep-alive",
            },
        )
        fake_mesh_server.post(
            "/messageexchange/MESH-TEST2/outbox/20210711164906010267_97CCD9/5",
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

        try:
            response = self.app.main(
                event=mock_input, context=MeshTestingCommon.CONTEXT
            )
        except Exception as e:  # pylint: disable=broad-except
            # need to fail happy pass on any exception
            self.fail(f"Invocation crashed with Exception {str(e)}")

        history = fake_mesh_server.request_history
        body1 = response["body"]

        try:
            response = self.app.main(
                event=mock_input, context=MeshTestingCommon.CONTEXT
            )
        except Exception as e:  # pylint: disable=broad-except
            # need to fail happy pass on any exception
            self.fail(f"Invocation crashed with Exception {str(e)}")

        try:
            response = self.app.main(
                event=mock_input, context=MeshTestingCommon.CONTEXT
            )
        except Exception as e:  # pylint: disable=broad-except
            # need to fail happy pass on any exception
            self.fail(f"Invocation crashed with Exception {str(e)}")

        with self.assertRaises(MaxByteExceededException) as context:
            self.app.main(
                event=mock_input, context=MeshTestingCommon.CONTEXT
            )
        self.assertIsInstance(context.exception, MaxByteExceededException)

        # Can't test like this with chunking!
        # self.assertEqual(self.app.body, MeshTestingCommon.FILE_CONTENT.encode("utf8"))

        # response["body"].pop("message_id")
        # self.assertDictEqual(mock_response, response)
        #
        # # Check completion
        # self.assertTrue(
        #     self.log_helper.was_value_logged("LAMBDA0003", "Log_Level", "INFO")
        # )

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
                "total_chunks": 5,
                "chunk_size": 10,
                "complete": False,
                "current_byte_position": 0,
                "compress_ratio": 1,
                "will_compress": False,
            },
        }
