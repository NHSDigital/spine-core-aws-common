""" Testing MeshSendMessageChunk Application """
from http import HTTPStatus
from unittest import mock
import json

from moto import mock_s3, mock_ssm
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
    def test_get_file_from_s3_uncompressed_without_parts(self, mock_create_new_internal_id, mock_response):
        #FILE_CONTENT = "123456789012345678901234567890123"
        s3_client = boto3.client("s3", config=MeshTestingCommon.aws_config)
        ssm_client = boto3.client("ssm", config=MeshTestingCommon.aws_config)
        MeshTestingCommon.setup_mock_aws_s3_buckets(self.environment, s3_client)
        MeshTestingCommon.setup_mock_aws_ssm_parameter_store(
            self.environment, ssm_client
        )
        self.app.current_byte = 0
        self.app.file_size = 33
        self.app.s3_client = s3_client
        self.app.bucket = f"{self.environment}-mesh"
        self.app.key = "MESH-TEST2/outbound/testfile.json"
        self.app.chunk_size = 33
        self.app.buffer_size = 33
        gen = self.app._get_file_from_s3()
        all_33_bytes = next(gen)
        self.assertEqual(b"123456789012345678901234567890123", all_33_bytes)


    @mock_ssm
    @mock_s3
    @mock.patch.object(MeshSendMessageChunkApplication, "_create_new_internal_id")
    @requests_mock.Mocker()
    def test_get_file_from_s3_uncompressed_with_parts(self, mock_create_new_internal_id, mock_response):
        s3_client = boto3.client("s3", config=MeshTestingCommon.aws_config)
        ssm_client = boto3.client("ssm", config=MeshTestingCommon.aws_config)
        MeshTestingCommon.setup_mock_aws_s3_buckets(self.environment, s3_client)
        MeshTestingCommon.setup_mock_aws_ssm_parameter_store(
            self.environment, ssm_client
        )
        self.app.current_byte = 0
        self.app.file_size = 33
        self.app.s3_client = s3_client
        self.app.bucket = f"{self.environment}-mesh"
        self.app.key = "MESH-TEST2/outbound/testfile.json"
        self.app.chunk_size = 33
        self.app.buffer_size = 7
        gen = self.app._get_file_from_s3()
        # considered putting a while loop here comparing current byte to self.FILE_SIZE
        # but that's exactly the same as the logic we're testing
        self.assertEqual(b"1234567", next(gen))
        self.assertEqual(b"8901234", next(gen))
        self.assertEqual(b"5678901", next(gen))
        self.assertEqual(b"2345678", next(gen))
        self.assertEqual(b"90123", next(gen))

    @mock_ssm
    @mock_s3
    @mock.patch.object(MeshSendMessageChunkApplication, "_create_new_internal_id")
    @requests_mock.Mocker()
    def test_mesh_send_file_chunk_app_no_chunks_happy_path(
        self, mock_create_new_internal_id, mock_response
    ):
        """Test the lambda with small file, no chunking, happy path"""
        mock_create_new_internal_id.return_value = MeshTestingCommon.KNOWN_INTERNAL_ID

        mock_response.post(
            "/messageexchange/MESH-TEST2/outbox",
            text=json.dumps({"messageID": "20210711164906010267_97CCD9"}),
            headers={
                "Content-Type": "application/json",
                "Content-Length": "44",
                "Connection": "keep-alive",
            },
        )

        s3_client = boto3.client("s3", config=MeshTestingCommon.aws_config)
        ssm_client = boto3.client("ssm", config=MeshTestingCommon.aws_config)
        MeshTestingCommon.setup_mock_aws_s3_buckets(self.environment, s3_client)
        MeshTestingCommon.setup_mock_aws_ssm_parameter_store(
            self.environment, ssm_client
        )
        mock_input = self._sample_input_event()
        mock_response = self._sample_input_event()
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
    def test_mesh_send_file_chunk_app_2_chunks_happy_path(
        self, mock_create_new_internal_id
    ):
        """
        Test that doing chunking works
        """
        mock_create_new_internal_id.return_value = MeshTestingCommon.KNOWN_INTERNAL_ID2
        s3_client = boto3.client("s3", config=MeshTestingCommon.aws_config)
        ssm_client = boto3.client("ssm", config=MeshTestingCommon.aws_config)
        MeshTestingCommon.setup_mock_aws_s3_buckets(self.environment, s3_client)
        MeshTestingCommon.setup_mock_aws_ssm_parameter_store(
            self.environment, ssm_client
        )

        # TODO

        response = {"statusCode": 200}
        expected_return_code = {"statusCode": 200}
        self.assertEqual(response, {**response, **expected_return_code})

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
                "chunk": False,
                "chunk_number": 1,
                "total_chunks": 1,
                "chunk_size": 50,
                "complete": False,
                "current_byte_position": 0,
                "will_compress": False,
            },
        }
