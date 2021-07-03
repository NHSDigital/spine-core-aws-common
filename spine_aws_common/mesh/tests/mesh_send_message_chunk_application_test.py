""" Testing MeshPollMailbox application """
from unittest import mock, TestCase
import boto3
from moto import mock_s3, mock_ssm, mock_stepfunctions
from spine_aws_common.mesh.tests.mesh_test_common import MeshTestCommon
from spine_aws_common.tests.utils.log_helper import LogHelper
from spine_aws_common.mesh import MeshSendMessageChunkApplication
from spine_aws_common.mesh.mesh_common import SingletonCheckFailure


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

        self.app = MeshSendMessageChunkApplication()
        self.environment = self.app.system_config["ENV"]

    def setup_mock_aws_environment(self, s3_client, ssm_client):
        """Setup standard environment for tests"""
        location = {"LocationConstraint": "eu-west-2"}
        s3_client.create_bucket(
            Bucket=f"{self.environment}-supplementary-data",
            CreateBucketConfiguration=location,
        )
        file_content = "123456789012345678901234567890123"
        s3_client.put_object(
            Bucket=f"{self.environment}-supplementary-data",
            Key="outbound/testfile.json",
            Body=file_content,
        )

    def tearDown(self) -> None:
        self.log_helper.clean_up()

    @mock_ssm
    @mock_s3
    def test_mesh_send_file_chunk_app_no_chunks_happy_path(self):
        """Test the lambda as a whole, happy path"""

        s3_client = boto3.client("s3")
        ssm_client = boto3.client("ssm")
        self.setup_mock_aws_environment(s3_client, ssm_client)
        mock_input = {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": {
                "internal_id": MeshTestCommon.KNOWN_INTERNAL_ID,
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
                "message_id": None,
            },
        }

        mock_response = {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": {
                "internal_id": MeshTestCommon.KNOWN_INTERNAL_ID,
                "src_mailbox": "X12XY123",
                "dest_mailbox": "A12AB123",
                "workflow_id": "TESTWORKFLOW",
                "bucket": f"{self.environment}-supplementary-data",
                "key": "outbound/testfile.json",
                "chunk": False,
                "chunk_number": 1,
                "total_chunks": 1,
                "chunk_size": 50,
                "complete": True,
                "message_id": "FAKE_MESH_MESSAGE_ID",
            },
        }
        try:
            response = self.app.main(event=mock_input, context=MeshTestCommon.CONTEXT)
        except Exception as e:  # pylint: disable=broad-except
            # need to fail happy pass on any exception
            self.fail(f"Invocation crashed with Exception {str(e)}")

        self.assertEqual(mock_response, response)
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
        self.setup_mock_aws_environment(s3_client, ssm_client)

        response = {}
        expected_return_code = {"statusCode": 200}
        self.assertEqual(response, {**response, **expected_return_code})
        self.assertTrue(
            self.log_helper.was_value_logged("MESHSEND0003", "Log_Level", "ERROR")
        )
        self.assertFalse(
            self.log_helper.was_value_logged("MESHSEND0004", "Log_Level", "INFO")
        )


def sample_trigger_event():
    """Return Example S3 eventbridge event"""
    return_value = {
        "version": "0",
        "id": "daea9bec-2d16-e943-2079-4d19b6e2ec1d",
        "detail-type": "AWS API Call via CloudTrail",
        "source": "aws.s3",
        "account": "123456789012",
        "time": "2021-06-29T14:10:55Z",
        "region": "eu-west-2",
        "resources": [],
        "detail": {
            "eventVersion": "1.08",
            "eventTime": "2021-06-29T14:10:55Z",
            "eventSource": "s3.amazonaws.com",
            "eventName": "PutObject",
            "awsRegion": "eu-west-2",
            "requestParameters": {
                "X-Amz-Date": "20210629T141055Z",
                "bucketName": "meshtest-supplementary-data",
                "X-Amz-Algorithm": "AWS4-HMAC-SHA256",
                "x-amz-acl": "private",
                "X-Amz-SignedHeaders": "content-md5;content-type;host;x-amz-acl;x-amz-storage-class",  # noqa pylint: disable=line-too-long
                "Host": "meshtest-supplementary-data.s3.eu-west-2.amazonaws.com",
                "X-Amz-Expires": "300",
                "key": "outbound/testfile.json",
                "x-amz-storage-class": "STANDARD",
            },
            "responseElements": {
                "x-amz-server-side-encryption": "aws:kms",
                "x-amz-server-side-encryption-aws-kms-key-id": "arn:aws:kms:eu-west-2:092420156801:key/4f295c4c-17fd-4c9d-84e9-266b01de0a5a",  # noqa pylint: disable=line-too-long
            },
            "requestID": "1234567890123456",
            "eventID": "75e91cfc-f2db-4e09-8f80-a206ab4cd15e",
            "readOnly": False,
            "resources": [
                {
                    "type": "AWS::S3::Object",
                    "ARN": "arn:aws:s3:::meshtest-supplementary-data/outbound/testfile.json",  # noqa pylint: disable=line-too-long
                },
                {
                    "accountId": "123456789012",
                    "type": "AWS::S3::Bucket",
                    "ARN": "arn:aws:s3:::meshtest-supplementary-data",
                },
            ],
            "eventType": "AwsApiCall",
            "managementEvent": False,
            "recipientAccountId": "123456789012",
            "eventCategory": "Data",
        },
    }
    # pylint: enable=line-too-long
    return return_value
