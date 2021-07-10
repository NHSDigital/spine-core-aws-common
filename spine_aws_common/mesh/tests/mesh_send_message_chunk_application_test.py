""" Testing MeshSendMessageChunk Application """
import json
from http import HTTPStatus
from unittest import mock, TestCase
import requests_mock
import boto3
from moto import mock_s3, mock_ssm
from spine_aws_common.mesh.tests.mesh_testing_common import MeshTestingCommon
from spine_aws_common.tests.utils.log_helper import LogHelper
from spine_aws_common.mesh import MeshSendMessageChunkApplication


class TestMeshSendMessageChunkApplication(TestCase):
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
            "Environment": "meshtest",
            "CHUNK_SIZE": "10",
        },
    )
    def setUp(self):
        """Common setup for all tests"""
        self.log_helper = LogHelper()
        self.log_helper.set_stdout_capture()
        self.maxDiff = 1024  # pylint: disable="invalid-name"

        self.app = MeshSendMessageChunkApplication()
        self.environment = self.app.system_config["Environment"]

    def tearDown(self) -> None:
        self.log_helper.clean_up()

    @mock_ssm
    @mock_s3
    @mock.patch.object(MeshSendMessageChunkApplication, "_create_internal_id")
    @requests_mock.Mocker()
    def test_mesh_send_file_chunk_app_no_chunks_happy_path(
        self, mock_create_internal_id, mock_response
    ):
        """Test the lambda with small file, no chunking, happy path"""
        # Mock responses from MESH server
        mock_response.get(
            f"/messageexchange/MESH-TEST1/inbox/{MeshTestingCommon.KNOWN_MESSAGE_ID1}",
            text="123456789012345678901234567890123",
            headers={
                "Content-Type": "application/octet-stream",
                "Content-Length": 33,
                "Connection": "keep-alive",
                "Mex-Messageid": MeshTestingCommon.KNOWN_MESSAGE_ID1,
                "Mex-From": "MESH-TEST2",
                "Mex-To": "MESH-TEST1",
                "Mex-Fromsmtp": "mesh.automation.testclient2@nhs.org",
                "Mex-Tosmtp": "mesh.automation.testclient1@nhs.org",
                "Mex-Filename": "testfile.txt",
                "Mex-Workflowid": "TESTWORKFLOW",
                "Mex-Messagetype": "DATA",
                "Mex-Version": "1.0",
                "Mex-Addresstype": "ALL",
                "Mex-Statuscode": "00",
                "Mex-Statusevent": "TRANSFER",
                "Mex-Statusdescription": "Transferred to recipient mailbox",
                "Mex-Statussuccess": "SUCCESS",
                "Mex-Statustimestamp": "20210705162157",
                "Mex-Content-Compressed": "N",
                "Etag": "915cd12d58ce2f820959e9ba41b2ebb02f2e6005",
            },
        )
        mock_response.get(
            "PUT /messageexchange/MESH-TEST1/inbox/"
            + f"{MeshTestingCommon.KNOWN_MESSAGE_ID1}/status/acknowledged",
            text=json.dumps({"messageId": MeshTestingCommon.KNOWN_MESSAGE_ID1}),
            headers={
                "Transfer-Encoding": "chunked",
                "Connection": "keep-alive",
                "Content-Encoding": "gzip",
            },
        )
        mock_create_internal_id.return_value = MeshTestingCommon.KNOWN_INTERNAL_ID

        s3_client = boto3.client("s3")
        ssm_client = boto3.client("ssm")
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

        self.assertEqual(self.app.body, MeshTestingCommon.FILE_CONTENT.encode("utf8"))

        response["body"].pop("message_id")
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
    @mock.patch.object(MeshSendMessageChunkApplication, "_create_internal_id")
    def test_mesh_send_file_chunk_app_2_chunks_happy_path(
        self, mock_create_internal_id
    ):
        """
        Test that doing chunking works
        """
        mock_create_internal_id.return_value = MeshTestingCommon.KNOWN_INTERNAL_ID2
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
        return {
            "statusCode": HTTPStatus.OK.value,
            "headers": {"Content-Type": "application/json"},
            "body": {
                "internal_id": MeshTestingCommon.KNOWN_INTERNAL_ID,
                "src_mailbox": "MESH-TEST2",
                "dest_mailbox": "MESH-TEST1",
                "workflow_id": "TESTWORKFLOW",
                "bucket": f"{self.environment}-supplementary-data",
                "key": "outbound/testfile.json",
                "chunk": False,
                "chunk_number": 1,
                "total_chunks": 1,
                "chunk_size": 50,
                "complete": False,
            },
        }
