"""Common methods and classes used for testing mesh client"""

FILE_CONTENT = "123456789012345678901234567890123"


class MeshTestingCommon:
    """Mock helpers"""

    CONTEXT = {"aws_request_id": "TESTREQUEST"}
    KNOWN_INTERNAL_ID = "20210701225219765177_TESTER"
    FILE_CONTENT = FILE_CONTENT

    def get_known_internal_id(self):  # pylint: disable=no-self-use
        """Get a known internal Id for testing and mocking purposes"""
        return "20210701225219765177_TESTER"

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
            Bucket=f"{environment}-supplementary-data",
            CreateBucketConfiguration=location,
        )
        file_content = FILE_CONTENT
        s3_client.put_object(
            Bucket=f"{environment}-supplementary-data",
            Key="outbound/testfile.json",
            Body=file_content,
        )

    @staticmethod
    def setup_mock_aws_ssm_parameter_store(environment, ssm_client):
        """Setup ssm param store for tests"""
        # Setup mapping
        print(f"Setting up mock parameter store for {environment}")
        ssm_client.put_parameter(
            Name=f"/{environment}/mesh/mapping/"
            + f"{environment}-supplementary-data/outbound/src_mailbox",
            Value="MESH-TEST2",
        )
        ssm_client.put_parameter(
            Name=f"/{environment}/mesh/mapping/"
            + f"{environment}-supplementary-data/outbound/dest_mailbox",
            Value="MESH-TEST1",
        )
        ssm_client.put_parameter(
            Name=f"/{environment}/mesh/mapping/"
            + f"{environment}-supplementary-data/outbound/workflow_id",
            Value="TESTWORKFLOW",
        )
        # Setup secrets
        ssm_client.put_parameter(
            Name=f"/{environment}/mesh/MESH_URL",
            Value="https://192.168.100.129",
        )
        ssm_client.put_parameter(
            Name=f"/{environment}/mesh/MESH_SHARED_KEY",
            Value="BackBone",
        )
        ssm_client.put_parameter(
            Name=f"/{environment}/mesh/mailboxes/MESH-TEST1/MESH_MAILBOX_PASSWORD",
            Value="pwd123456",
        )
        ssm_client.put_parameter(
            Name=f"/{environment}/mesh/mailboxes/MESH-TEST2/MESH_MAILBOX_PASSWORD",
            Value="pwd123456",
        )
        ssm_client.put_parameter(
            Name=f"/{environment}/mesh/MESH_VERIFY_SSL",
            Value="False",
        )
        with open("ca.crt", "r") as ca_cert_file:
            ca_cert = ca_cert_file.read()
            ssm_client.put_parameter(
                Name=f"/{environment}/mesh/MESH_CA_CERT",
                Value=ca_cert,
            )
            ca_cert_file.close()
        with open("client-sha2.crt", "r") as client_cert_file:
            client_cert = client_cert_file.read()
            ssm_client.put_parameter(
                Name=f"/{environment}/mesh/MESH_CLIENT_CERT",
                Value=client_cert,
            )
            client_cert_file.close()
        with open("client-sha2.key", "r") as client_key_file:
            client_key = client_key_file.read()
            ssm_client.put_parameter(
                Name=f"/{environment}/mesh/MESH_CLIENT_KEY",
                Value=client_key,
            )
            client_key_file.close()
