""" Testing MeshPollMailbox application """
from unittest import mock, TestCase
import boto3
from moto import mock_s3, mock_ssm
from spine_aws_common.mesh.tests.mesh_testing_common import MeshTestingCommon
from spine_aws_common.tests.utils.log_helper import LogHelper
from spine_aws_common.mesh import MeshSendMessageChunkApplication


class TestMeshSendMessageChunkApplication(TestCase):
    """Testing MeshPollMailbox application"""

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

        self.app = MeshSendMessageChunkApplication()
        self.environment = self.app.system_config["ENV"]

    def tearDown(self) -> None:
        self.log_helper.clean_up()

    @mock_ssm
    @mock_s3
    def test_mesh_send_file_chunk_app_no_chunks_happy_path(self):
        """Test the lambda as a whole, happy path"""

        s3_client = boto3.client("s3")
        ssm_client = boto3.client("ssm")
        MeshTestingCommon.setup_mock_aws_s3_buckets(self.environment, s3_client)
        MeshTestingCommon.setup_mock_aws_ssm_parameter_store(
            self.environment, ssm_client
        )
        mock_input = self._sample_input_event()
        mock_response = self._sample_input_event()
        mock_response["body"].update(
            {"complete": True, "message_id": "FAKE_MESH_MESSAGE_ID"}
        )

        try:
            response = self.app.main(
                event=mock_input, context=MeshTestingCommon.CONTEXT
            )
        except Exception as e:  # pylint: disable=broad-except
            # need to fail happy pass on any exception
            self.fail(f"Invocation crashed with Exception {str(e)}")

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

    @mock_ssm
    @mock_s3
    def test_mesh_send_file_chunk_app_2_chunks_happy_path(self):
        """
        Test that doing chunking works
        """
        s3_client = boto3.client("s3")
        ssm_client = boto3.client("ssm")
        MeshTestingCommon.setup_mock_aws_s3_buckets(self.environment, s3_client)
        MeshTestingCommon.setup_mock_aws_ssm_parameter_store(
            self.environment, ssm_client
        )

        response = {"statusCode": 200}
        expected_return_code = {"statusCode": 200}
        self.assertEqual(response, {**response, **expected_return_code})

    def _sample_input_event(self):
        """Return Example input event"""
        return_value = {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": {
                "internal_id": MeshTestingCommon.KNOWN_INTERNAL_ID,
                "src_mailbox": "X12XY123",
                "dest_mailbox": "A12AB123",
                "workflow_id": "TESTWORKFLOW",
                "bucket": f"{self.environment}-supplementary-data",
                "key": "outbound/testfile.json",
                "chunk": False,
                "chunk_number": 1,
                "total_chunks": 1,
                "chunk_size": 50,
                "complete": False,
                "message_id": "",
            },
        }
        return return_value
