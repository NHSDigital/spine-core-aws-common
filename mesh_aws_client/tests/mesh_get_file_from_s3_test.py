""" Testing Get File From S3 Function """
from unittest import mock

from moto import mock_s3, mock_ssm
import boto3

from mesh_aws_client.mesh_send_message_chunk_application import (
    MeshSendMessageChunkApplication,
)
from mesh_aws_client.tests.mesh_testing_common import (
    MeshTestCase,
    MeshTestingCommon,
)


class TestMeshGetFileFromS3(MeshTestCase):
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

    # Need to test function within app, but it should be a private function
    # pylint: disable=protected-access
    @mock_ssm
    @mock_s3
    def test_get_file_from_s3_without_parts(self):
        """
        Test _get_file_from_s3 getting an uncompressed small file
        """
        # FILE_CONTENT = "123456789012345678901234567890123"
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
    def test_get_file_from_s3_with_parts(self):
        """
        Test _get_file_from_s3 getting an uncompressed large file
        """
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
        self.assertEqual(b"1234567", next(gen))
        self.assertEqual(b"8901234", next(gen))
        self.assertEqual(b"5678901", next(gen))
        self.assertEqual(b"2345678", next(gen))
        self.assertEqual(b"90123", next(gen))


# pylint: enable=protected-access
