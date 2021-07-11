""" Testing MeshPollMailbox application """
from unittest import mock, TestCase
from http import HTTPStatus
import boto3
from moto import mock_s3, mock_ssm, mock_stepfunctions
from spine_aws_common.mesh.tests.mesh_testing_common import MeshTestingCommon
from spine_aws_common.tests.utils.log_helper import LogHelper
from spine_aws_common.mesh import MeshCheckSendParametersApplication
from spine_aws_common.mesh.mesh_common import SingletonCheckFailure


# pylint:disable=duplicate-code
class TestMeshCheckSendParametersApplication(TestCase):
    """Testing MeshPollMailbox application"""

    def __init__(self, method_name):
        super().__init__(methodName=method_name)
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

        self.app = MeshCheckSendParametersApplication()
        self.environment = self.app.system_config["Environment"]

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
        MeshTestingCommon.setup_mock_aws_ssm_parameter_store(
            self.environment, ssm_client
        )

    def tearDown(self):
        self.log_helper.clean_up()

    @mock_stepfunctions
    @mock_ssm
    @mock_s3
    @mock.patch.object(
        MeshCheckSendParametersApplication,
        "_get_internal_id",
        MeshTestingCommon.get_known_internal_id,
    )
    def test_mesh_check_send_parameters_happy_path(self):
        """Test the lambda as a whole, happy path"""

        s3_client = boto3.client("s3", config=MeshTestingCommon.aws_config)
        ssm_client = boto3.client("ssm", config=MeshTestingCommon.aws_config)
        self.setup_mock_aws_environment(s3_client, ssm_client)
        sfn_client = boto3.client("stepfunctions", config=MeshTestingCommon.aws_config)
        response = MeshTestingCommon.setup_step_function(
            sfn_client,
            self.environment,
            f"{self.environment}-mesh-send-message",
        )

        mock_response = {
            "statusCode": HTTPStatus.OK.value,
            "headers": {"Content-Type": "application/json"},
            "body": {
                "internal_id": MeshTestingCommon.KNOWN_INTERNAL_ID,
                "src_mailbox": "MESH-TEST2",
                "dest_mailbox": "MESH-TEST1",
                "workflow_id": "TESTWORKFLOW",
                "bucket": f"{self.environment}-supplementary-data",
                "key": "outbound/testfile.json",
                "chunk": True,
                "chunk_number": 1,
                "total_chunks": 4,
                "chunk_size": 10,
                "complete": False,
                "message_id": None,
            },
        }
        try:
            response = self.app.main(
                event=sample_trigger_event(), context=MeshTestingCommon.CONTEXT
            )
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

    @mock_stepfunctions
    @mock_ssm
    @mock_s3
    @mock.patch.object(
        MeshCheckSendParametersApplication,
        "_get_internal_id",
        MeshTestingCommon.get_known_internal_id,
    )
    def test_running_as_singleton(self):
        """
        Test that the singleton check works correctly
        """
        s3_client = boto3.client("s3", config=MeshTestingCommon.aws_config)
        ssm_client = boto3.client("ssm", config=MeshTestingCommon.aws_config)
        self.setup_mock_aws_environment(s3_client, ssm_client)
        sfn_client = boto3.client("stepfunctions", config=MeshTestingCommon.aws_config)

        print("------------------------- TEST 1 -------------------------------")
        # define step function
        response = MeshTestingCommon.setup_step_function(
            sfn_client,
            self.environment,
            f"{self.environment}-mesh-send-message",
        )
        step_func_arn = response.get("stateMachineArn", None)
        self.assertIsNotNone(step_func_arn)

        # 'start' fake state machine
        response = sfn_client.start_execution(
            stateMachineArn=step_func_arn,
            input='{"mailbox": "MESH-TEST2"}',
        )
        step_func_exec_arn = response.get("executionArn", None)
        self.assertIsNotNone(step_func_exec_arn)

        # do running check - should pass (1 step function running, just mine)
        try:
            response = self.app.main(
                event=sample_trigger_event(), context=MeshTestingCommon.CONTEXT
            )
        except SingletonCheckFailure as e:
            self.fail(e.msg)
        self.assertIsNotNone(response)
        self.assertFalse(
            self.log_helper.was_value_logged("MESHSEND0003", "Log_Level", "ERROR")
        )
        self.assertTrue(
            self.log_helper.was_value_logged("MESHSEND0004", "Log_Level", "INFO")
        )
        self.log_helper.clean_up()

        print("------------------------- TEST 2 -------------------------------")
        self.log_helper.set_stdout_capture()

        # create another step function with a different name
        response = MeshTestingCommon.setup_step_function(
            sfn_client,
            self.environment,
            f"{self.environment}-mesh-get-messages",
        )
        step_func2_arn = response.get("stateMachineArn", None)
        self.assertIsNotNone(step_func2_arn)

        # 'start' state machine 2 with my mailbox
        response = sfn_client.start_execution(
            stateMachineArn=step_func2_arn,
            input='{"mailbox": "MESH-TEST2"}',
        )
        step_func_exec_arn = response.get("executionArn", None)
        self.assertIsNotNone(step_func_exec_arn)

        # do running check - should pass (1 step function of my name with my mailbox)
        try:
            response = self.app.main(
                event=sample_trigger_event(), context=MeshTestingCommon.CONTEXT
            )
        except SingletonCheckFailure as e:
            self.fail(e.msg)
        self.assertIsNotNone(response)
        self.assertFalse(
            self.log_helper.was_value_logged("MESHSEND0003", "Log_Level", "ERROR")
        )
        self.assertTrue(
            self.log_helper.was_value_logged("MESHSEND0004", "Log_Level", "INFO")
        )
        self.log_helper.clean_up()

        print("------------------------- TEST 3 -------------------------------")
        self.log_helper.set_stdout_capture()

        # 'start' state machine with different mailbox
        response = sfn_client.start_execution(
            stateMachineArn=step_func_arn,
            input='{"mailbox": "SOMETHING-ELSE"}',
        )
        step_func_exec_arn = response.get("executionArn", None)
        self.assertIsNotNone(step_func_exec_arn)

        # do running check - should pass (1 step function running with my mailbox)
        try:
            response = self.app.main(
                event=sample_trigger_event(), context=MeshTestingCommon.CONTEXT
            )
        except SingletonCheckFailure as e:
            self.fail(e.msg)
        self.assertIsNotNone(response)
        self.assertFalse(
            self.log_helper.was_value_logged("MESHSEND0003", "Log_Level", "ERROR")
        )
        self.assertTrue(
            self.log_helper.was_value_logged("MESHSEND0004", "Log_Level", "INFO")
        )
        self.log_helper.clean_up()

        print("------------------------- TEST 4 -------------------------------")
        self.log_helper.set_stdout_capture()

        # 'start' another instance with same mailbox as mine
        response = sfn_client.start_execution(
            stateMachineArn=step_func_arn,
            input='{"mailbox": "MESH-TEST2"}',
        )
        step_func_exec_arn = response.get("executionArn", None)
        self.assertIsNotNone(step_func_exec_arn)
        # do running check - should return 503 and log MESHSEND0003 error message
        response = self.app.main(
            event=sample_trigger_event(), context=MeshTestingCommon.CONTEXT
        )
        expected_return_code = {"statusCode": HTTPStatus.TOO_MANY_REQUESTS.value}
        expected_header = {"Retry-After": 18000}
        self.assertEqual(response, {**response, **expected_return_code})
        self.assertEqual(
            response["headers"], {**response["headers"], **expected_header}
        )
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
