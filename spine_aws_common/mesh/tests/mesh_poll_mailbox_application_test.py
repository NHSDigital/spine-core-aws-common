""" Testing MeshPollMailbox application """

from http import HTTPStatus
import json
from unittest import mock, TestCase
import requests_mock
import boto3
from moto import mock_s3, mock_ssm, mock_stepfunctions
from spine_aws_common.mesh import MeshPollMailboxApplication
from spine_aws_common.mesh.tests.mesh_testing_common import MeshTestingCommon
from spine_aws_common.tests.utils.log_helper import LogHelper


class TestMeshPollMailboxApplication(TestCase):
    """Testing MeshPollMailbox application"""

    def __init__(self, method_name):
        super().__init__(methodName=method_name)

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
            "Environment": "meshtest",
            "CHUNK_SIZE": "10",
        },
    )
    def setUp(self):
        """Common setup for all tests"""
        self.log_helper = LogHelper()
        self.log_helper.set_stdout_capture()
        self.maxDiff = 1024  # pylint: disable="invalid-name"
        self.app = MeshPollMailboxApplication()
        self.environment = self.app.system_config["Environment"]

    def tearDown(self) -> None:
        super().tearDown()
        self.log_helper.clean_up()

    @mock_ssm
    @mock_s3
    @mock_stepfunctions
    @requests_mock.Mocker()
    def test_mesh_poll_mailbox_happy_path(self, mock_response):
        """Test the lambda"""

        # Mock response from MESH server
        mock_response.get(
            "/messageexchange/MESH-TEST1/inbox",
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

        mailbox_name = "MESH-TEST1"
        mock_input = {"mailbox": mailbox_name}
        s3_client = boto3.client("s3", region_name="eu-west-2")
        ssm_client = boto3.client("ssm", region_name="eu-west-2")
        MeshTestingCommon.setup_mock_aws_s3_buckets(self.environment, s3_client)
        MeshTestingCommon.setup_mock_aws_ssm_parameter_store(
            self.environment, ssm_client
        )
        sfn_client = boto3.client("stepfunctions", region_name="eu-west-2")
        response = MeshTestingCommon.setup_step_function(
            sfn_client,
            self.environment,
            self.app.my_step_function_name,
        )
        try:
            response = self.app.main(
                event=mock_input, context=MeshTestingCommon.CONTEXT
            )
        except Exception as e:  # pylint: disable=broad-except
            # need to fail happy pass on any exception
            self.fail(f"Invocation crashed with Exception {str(e)}")

        self.assertEqual(HTTPStatus.OK.value, response["statusCode"])
        # check 3 messages received
        self.assertEqual(3, response["body"]["message_count"])
        # check first message format in message_list
        self.assertEqual(
            MeshTestingCommon.KNOWN_MESSAGE_ID1,
            response["body"]["message_list"][0]["body"]["message_id"],
        )
        self.assertEqual(False, response["body"]["message_list"][0]["body"]["complete"])
        self.assertEqual(
            mailbox_name, response["body"]["message_list"][0]["body"]["dest_mailbox"]
        )
        # check the correct logs exist
        self.assertLogs("LAMBDA0001", level="INFO")
        self.assertLogs("LAMBDA0002", level="INFO")
        self.assertLogs("LAMBDA0003", level="INFO")
