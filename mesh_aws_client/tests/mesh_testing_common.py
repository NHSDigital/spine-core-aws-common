"""Common methods and classes used for testing mesh client"""
from unittest import TestCase

from botocore.config import Config
from moto import mock_s3, mock_ssm

from spine_aws_common.log.log_helper import LogHelper

FILE_CONTENT = "123456789012345678901234567890123"


class MeshTestingCommon:
    """Mock helpers"""

    CONTEXT = {"aws_request_id": "TESTREQUEST"}
    KNOWN_INTERNAL_ID = "20210701225219765177_TESTER"
    KNOWN_INTERNAL_ID1 = "20210701225219765177_TEST01"
    KNOWN_INTERNAL_ID2 = "20210701225219765177_TEST02"
    KNOWN_MESSAGE_ID1 = "20210704225941465332_MESG01"
    KNOWN_MESSAGE_ID2 = "20210705133616577537_MESG02"
    KNOWN_MESSAGE_ID3 = "20210705134726725149_MESG03"
    FILE_CONTENT = FILE_CONTENT

    aws_config = Config(region_name="eu-west-2")

    os_environ_values = {
        "AWS_REGION": "eu-west-2",
        "AWS_EXECUTION_ENV": "AWS_Lambda_python3.8",
        "AWS_LAMBDA_FUNCTION_NAME": "lambda_test",
        "AWS_LAMBDA_FUNCTION_MEMORY_SIZE": "128",
        "AWS_LAMBDA_FUNCTION_VERSION": "1",
        "Environment": "meshtest",
        "CHUNK_SIZE": "10",
    }

    @classmethod
    def get_known_internal_id(cls):
        """Get a known internal Id for testing and mocking purposes"""
        return MeshTestingCommon.KNOWN_INTERNAL_ID

    @classmethod
    def get_known_internal_id1(cls):
        """Get a known internal Id for testing and mocking purposes"""
        return MeshTestingCommon.KNOWN_INTERNAL_ID1

    @classmethod
    def get_known_internal_id2(cls):
        """Get a known internal Id for testing and mocking purposes"""
        return MeshTestingCommon.KNOWN_INTERNAL_ID2

    @staticmethod
    def setup_step_function(sfn_client, environment, step_function_name):
        """Setup a mock step function with name from environment"""
        if not environment:
            environment = "default"
        step_func_definition = {
            "Comment": "Test step function",
            "StartAt": "HelloWorld",
            "States": {
                "HelloWorld": {
                    "Type": "Task",
                    "Resource": "arn:aws:lambda:eu-west-2:123456789012:function:HW",
                    "End": True,
                }
            },
        }
        return sfn_client.create_state_machine(
            definition=f"{step_func_definition}",
            loggingConfiguration={
                "destinations": [{"cloudWatchLogsLogGroup": {"logGroupArn": "xxx"}}],
                "includeExecutionData": False,
                "level": "ALL",
            },
            name=step_function_name,
            roleArn="arn:aws:iam::123456789012:role/StepFunctionRole",
            tags=[{"key": "environment", "value": environment}],
            tracingConfiguration={"enabled": False},
            type="STANDARD",
        )

    @staticmethod
    def setup_mock_aws_s3_buckets(environment, s3_client):
        """Setup standard environment for tests"""
        location = {"LocationConstraint": "eu-west-2"}
        s3_client.create_bucket(
            Bucket=f"{environment}-mesh",
            CreateBucketConfiguration=location,
        )
        file_content = FILE_CONTENT
        s3_client.put_object(
            Bucket=f"{environment}-mesh",
            Key="MESH-TEST2/outbound/testfile.json",
            Body=file_content,
            Metadata={
                "Mex-subject": "Custom Subject",
            },
        )

    @staticmethod
    def setup_mock_aws_ssm_parameter_store(environment, ssm_client):
        """Setup ssm param store for tests"""
        # Setup mapping
        ssm_client.put_parameter(
            Name=f"/{environment}/mesh/mapping/"
            + f"{environment}-mesh/MESH-TEST2/outbound/src_mailbox",
            Value="MESH-TEST2",
        )
        ssm_client.put_parameter(
            Name=f"/{environment}/mesh/mapping/"
            + f"{environment}-mesh/MESH-TEST2/outbound/dest_mailbox",
            Value="MESH-TEST1",
        )
        ssm_client.put_parameter(
            Name=f"/{environment}/mesh/mapping/"
            + f"{environment}-mesh/MESH-TEST2/outbound/workflow_id",
            Value="TESTWORKFLOW",
        )
        # Setup secrets
        ssm_client.put_parameter(
            Name=f"/{environment}/mesh/MESH_URL",
            Value="https://localhost",
        )
        ssm_client.put_parameter(
            Name=f"/{environment}/mesh/MESH_SHARED_KEY",
            Value="BackBone",
        )
        ssm_client.put_parameter(
            Name=f"/{environment}/mesh/mailboxes/MESH-TEST1/MAILBOX_PASSWORD",
            Value="pwd123456",
        )
        ssm_client.put_parameter(
            Name=f"/{environment}/mesh/mailboxes/MESH-TEST1/INBOUND_BUCKET",
            Value=f"{environment}-mesh",
        )
        ssm_client.put_parameter(
            Name=f"/{environment}/mesh/mailboxes/MESH-TEST1/INBOUND_FOLDER",
            Value="inbound-mesh-test1",
        )
        ssm_client.put_parameter(
            Name=f"/{environment}/mesh/mailboxes/MESH-TEST2/MAILBOX_PASSWORD",
            Value="pwd123456",
        )
        ssm_client.put_parameter(
            Name=f"/{environment}/mesh/mailboxes/MESH-TEST2/INBOUND_BUCKET",
            Value=f"{environment}-mesh",
        )
        ssm_client.put_parameter(
            Name=f"/{environment}/mesh/mailboxes/MESH-TEST2/INBOUND_FOLDER",
            Value="inbound-mesh-test2",
        )
        ssm_client.put_parameter(
            Name=f"/{environment}/mesh/MESH_VERIFY_SSL",
            Value="False",
        )
        ca_cert = "BLAH"
        client_cert = "BLAH"
        client_key = "BLAH"
        ssm_client.put_parameter(
            Name=f"/{environment}/mesh/MESH_CA_CERT",
            Value=ca_cert,
        )
        ssm_client.put_parameter(
            Name=f"/{environment}/mesh/MESH_CLIENT_CERT",
            Value=client_cert,
        )
        ssm_client.put_parameter(
            Name=f"/{environment}/mesh/MESH_CLIENT_KEY",
            Value=client_key,
        )


class MeshTestCase(TestCase):
    """Common setup for Mesh test cases"""

    def __init__(self, method_name):
        super().__init__(methodName=method_name)
        self.environment = None
        self.app = None

    @mock_s3
    @mock_ssm
    def setUp(self):
        """Common setup for all tests"""
        self.log_helper = LogHelper()
        self.log_helper.set_stdout_capture()

    def tearDown(self):
        self.log_helper.clean_up()
