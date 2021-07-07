""" Testing MeshSendMessageChunk Application """
from unittest import mock, TestCase
from http import HTTPStatus
import boto3
from moto import mock_s3, mock_ssm
from spine_aws_common.mesh.tests.mesh_testing_common import MeshTestingCommon
from spine_aws_common.tests.utils.log_helper import LogHelper
from spine_aws_common.mesh import MeshFetchMessageChunkApplication


class TestMeshFetchMessageChunkApplication(TestCase):
    """Testing MeshSendMessageChunk application"""

    def __init__(self, methodName):
        super().__init__(methodName=methodName)
        self.environment = None

    @mock_ssm
    @mock_s3
    @mock.patch.dict(
        "os.environ",
        values={
            "AWS_REGION": "eu-west-2",
            "AWS_EXECUTION_ENV": "AWS_Lambda_python3.8",
            "AWS_LAMBDA_FUNCTION_NAME": "lambda_test",
            "AWS_LAMBDA_FUNCTION_MEMORY_SIZE": "128",
            "AWS_LAMBDA_FUNCTION_VERSION": "1",
            "ENV": "meshtest",
            "CHUNK_SIZE": "10",
        },
    )
    def setUp(self):
        """Common setup for all tests"""
        self.log_helper = LogHelper()
        self.log_helper.set_stdout_capture()
        self.maxDiff = 1024  # pylint: disable="invalid-name"

        self.app = MeshFetchMessageChunkApplication()
        self.environment = self.app.system_config["ENV"]

    def tearDown(self) -> None:
        self.log_helper.clean_up()

    @mock_ssm
    @mock_s3
    @mock.patch.object(MeshFetchMessageChunkApplication, "_create_new_internal_id")
    def test_mesh_fetch_file_chunk_app_no_chunks_happy_path(
        self, mock_create_new_internal_id
    ):
        """Test the lambda with small file, no chunking, happy path"""
        mock_create_new_internal_id.return_value = MeshTestingCommon.KNOWN_INTERNAL_ID2
        s3_client = boto3.client("s3")
        ssm_client = boto3.client("ssm")
        MeshTestingCommon.setup_mock_aws_s3_buckets(self.environment, s3_client)
        MeshTestingCommon.setup_mock_aws_ssm_parameter_store(
            self.environment, ssm_client
        )
        mock_input = self._sample_first_input_event()
        mock_response = self._sample_second_input_event()

        mock_response["body"].update({"complete": True, "chunk_num": 1})

        try:
            response = self.app.main(
                event=mock_input, context=MeshTestingCommon.CONTEXT
            )
        except Exception as e:  # pylint: disable=broad-except
            # need to fail happy pass on any exception
            self.fail(f"Invocation crashed with Exception {str(e)}")

        print(response)
        self.assertNotEqual(
            mock_input.get("internal_id"), response["body"].get("internal_id")
        )
        self.assertEqual(
            response["body"].get("internal_id"),
            mock_response["body"].get("internal_id"),
        )
        self.assertDictEqual(mock_response, response)
        self.assertTrue(
            self.log_helper.was_value_logged("LAMBDA0001", "Log_Level", "INFO")
        )
        self.assertTrue(
            self.log_helper.was_value_logged("LAMBDA0002", "Log_Level", "INFO")
        )
        self.assertTrue(
            self.log_helper.was_value_logged("LAMBDA0003", "Log_Level", "INFO")
        )

    # @mock_ssm
    # @mock_s3
    # def test_mesh_fetch_file_chunk_app_2_chunks_happy_path(self):
    #     """
    #     Test that doing chunking works
    #     """
    #     s3_client = boto3.client("s3")
    #     ssm_client = boto3.client("ssm")
    #     MeshTestingCommon.setup_mock_aws_s3_buckets(self.environment, s3_client)
    #     MeshTestingCommon.setup_mock_aws_ssm_parameter_store(
    #         self.environment, ssm_client
    #     )

    #     response = {"statusCode": HTTPStatus.OK.value}
    #     expected_return_code = {"statusCode": HTTPStatus.OK.value}
    #     self.assertEqual(response, {**response, **expected_return_code})

    @staticmethod
    def _sample_first_input_event():
        return {
            "statusCode": HTTPStatus.OK.value,
            "headers": {"Content-Type": "application/json"},
            "body": {
                "complete": False,
                "internal_id": MeshTestingCommon.KNOWN_INTERNAL_ID1,
                "message_id": MeshTestingCommon.KNOWN_MESSAGE_ID,
                "dest_mailbox": "MESH-TEST1",
            },
        }

    @staticmethod
    def _sample_second_input_event():
        return {
            "statusCode": HTTPStatus.OK.value,
            "headers": {"Content-Type": "application/json"},
            "body": {
                "complete": False,
                "internal_id": MeshTestingCommon.KNOWN_INTERNAL_ID2,
                "message_id": MeshTestingCommon.KNOWN_MESSAGE_ID,
                "dest_mailbox": "MESH-TEST1",
                "chunk_num": 2,
                "aws_upload_id": None,
            },
        }
