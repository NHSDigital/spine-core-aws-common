# pylint:disable=protected-access
"""
Lambda Testing
"""
from unittest import mock, TestCase
from aws_lambda_powertools.utilities.typing.lambda_context import LambdaContext

from spine_aws_common.tests.utils.log_helper import LogHelper
from spine_aws_common import LambdaApplication

from moto import mock_lambda, mock_iam, mock_sns, mock_sqs
import boto3

import io
import zipfile
import json

from botocore.exceptions import ClientError

os.environ["AWS_DEFAULT_REGION"] = "eu-west-2"


class TestLambdaApplication(TestCase):
    """Testing Lambda application"""

    maxDiff = None

    def setUp(self):
        self.log_helper = LogHelper()
        self.log_helper.set_stdout_capture()

        self.app = LambdaApplication()

    def tearDown(self) -> None:
        self.log_helper.clean_up()

    # pylint:disable=duplicate-code
    @mock.patch.dict(
        "os.environ",
        values={
            "AWS_REGION": "eu-west-2",
            "AWS_EXECUTION_ENV": "AWS_Lambda_python3.8",
            "AWS_LAMBDA_FUNCTION_NAME": "lambda_test",
            "AWS_LAMBDA_FUNCTION_MEMORY_SIZE": "128",
            "AWS_LAMBDA_FUNCTION_VERSION": "1",
        },
    )
    def test_lambda(self):
        """Testing the initialisation of the lambda"""
        event = {
            "version": "0",
            "id": "d77bcbc4-0b2b-4d45-9694-b1df99175cfb",
            "detail-type": "Scheduled Event",
            "source": "aws.events",
            "account": "123456789",
            "time": "2016-09-25T04:55:26Z",
            "region": "eu-west-2",
            "resources": ["arn:aws:events:eu-west-2:123456789:rule/test-service-rule"],
            "detail": {},
        }
        response = self.app.main(event=event, context=None)
        response_mock = {"message": "Lambda application stopped"}
        self.assertEqual(response_mock, response)
        self.log_helper.was_logged("LAMBDA0001")
        self.assertTrue(
            self.log_helper.was_value_logged("LAMBDA0001", "Log_Level", "INFO")
        )

        self.assertTrue(
            self.log_helper.was_value_logged("LAMBDA0002", "Log_Level", "INFO")
        )

        self.assertTrue(
            self.log_helper.was_value_logged("LAMBDA0003", "Log_Level", "INFO")
        )

    def test_lambda_additional_logging(self):
        """Testing the initialisation of the lambda with extra logging config"""
        app = LambdaApplication(additional_log_config=f"{__file__}/add_config.cfg")
        app.log_object.write_log(
            "ADDTEST001",
            None,
            None,
        )

        self.assertTrue(
            self.log_helper.was_value_logged("ADDTEST001", "Log_Level", "INFO")
        )

    def test_logging_using_context_dict(self):
        """Testing that the logging can get the request id"""
        self.app.context = {"aws_request_id": "test"}
        self.app._log_start()

        self.assertTrue(
            self.log_helper.was_value_logged("LAMBDA0002", "aws_request_id", "test")
        )

    def test_logging_using_context_dict_missing_key(self):
        """Testing that the logging can get the request id"""
        self.app.context = {}
        self.app._log_start()

        self.assertTrue(
            self.log_helper.was_value_logged("LAMBDA0002", "aws_request_id", "unknown")
        )

    def test_logging_using_context_object(self):
        """Testing that the logging can get the request id"""
        self.app.context = LambdaContext()
        self.app.context._aws_request_id = "test"
        self.app._log_start()

        self.assertTrue(
            self.log_helper.was_value_logged("LAMBDA0002", "aws_request_id", "test")
        )

    def test_logging_using_context_object_no_id(self):
        """Testing that the logging can get the request id"""
        self.app.context = LambdaContext()
        self.app._log_start()

        self.assertTrue(
            self.log_helper.was_value_logged("LAMBDA0002", "aws_request_id", "unknown")
        )

    def test_logging_using_context_unknown(self):
        """Testing that the logging can get the request id"""
        self.app.context = None
        self.app._log_start()

        self.assertTrue(
            self.log_helper.was_value_logged("LAMBDA0002", "aws_request_id", "unknown")
        )

    @mock_lambda
    def test_lambda_invoke(self):
        """Test that when an Lambda function is invoked from the application,
        the same internal_id is passed through to the invokated function"""
        self._mock_lambda_function(lambda_name="lambda_test")
        event = {
            "version": "0",
            "id": "d77bcbc4-0b2b-4d45-9694-b1df99175cfb",
            "detail-type": "Scheduled Event",
            "source": "aws.events",
            "account": "123456789",
            "time": "2016-09-25T04:55:26Z",
            "region": "eu-west-2",
            "resources": ["arn:aws:events:eu-west-2:123456789:rule/test-service-rule"],
            "detail": {},
            "internal_id": "1234_TEST",
        }
        self.app.main(event, {})
        response = self.app.invoke_lambda(Payload={}, FunctionName="lambda_test")
        response_payload = json.loads(response["Payload"].read().decode("UTF-8"))
        self.assertEqual(response_payload["internal_id"], "1234_TEST")

    @mock_sns
    def test_sns_publish(self):
        """Test that an SNS message can be published"""
        event = {
            "version": "0",
            "id": "d77bcbc4-0b2b-4d45-9694-b1df99175cfb",
            "detail-type": "Scheduled Event",
            "source": "aws.events",
            "account": "123456789",
            "time": "2016-09-25T04:55:26Z",
            "region": "eu-west-2",
            "resources": ["arn:aws:events:eu-west-2:123456789:rule/test-service-rule"],
            "detail": {},
            "internal_id": "1234_TEST",
        }
        message = {"foo": "bar"}
        self.app.main(event, {})
        response = self.app.sns_publish(
            TargetArn=self._mock_sns_topic("mocktopic"),
            Message=json.dumps({"default": json.dumps(message)}),
            MessageStructure="json",
            MessageAttributes={"foo": {"DataType": "String", "StringValue": "bar"}},
        )

        self.assertIn("MessageId", response)

    @mock_sqs
    def test_sqs_publish(self):
        event = {
            "version": "0",
            "id": "d77bcbc4-0b2b-4d45-9694-b1df99175cfb",
            "detail-type": "Scheduled Event",
            "source": "aws.events",
            "account": "123456789",
            "time": "2016-09-25T04:55:26Z",
            "region": "eu-west-2",
            "resources": ["arn:aws:events:eu-west-2:123456789:rule/test-service-rule"],
            "detail": {},
            "internal_id": "1234_TEST",
        }
        self.app.main(event, {})
        queueurl = self._mock_sqs_queue("mockqueue")
        response = self.app.sqs_publish(
            QueueUrl=queueurl,
            MessageBody="foo",
            MessageAttributes={"foo": {"DataType": "String", "StringValue": "bar"}},
        )

        self.assertIn("MessageId", response)

    def _get_test_zip_file(self):
        pfunc = """
def lambda_handler(event, context):
    return event
                """
        zip_output = io.BytesIO()
        zip_file = zipfile.ZipFile(zip_output, "w", zipfile.ZIP_DEFLATED)
        zip_file.writestr("lambda_function.py", pfunc)
        zip_file.close()
        zip_output.seek(0)
        return zip_output.read()

    def _mock_lambda_function(self, lambda_name):
        return boto3.client("lambda").create_function(
            FunctionName=lambda_name,
            Runtime="python3.8",
            Role=self._get_role_name(),
            Handler="lambda_function.lambda_handler",
            Code={
                "ZipFile": self._get_test_zip_file(),
            },
            Description="test lambda function",
            Timeout=3,
            MemorySize=128,
            Publish=True,
        )

    def _mock_sns_topic(self, topic_name):
        mock_topic = boto3.client("sns").create_topic(Name=topic_name)
        return mock_topic.get("TopicArn")

    def _mock_sqs_queue(self, queue_name):
        mock_queue = boto3.client("sqs").create_queue(QueueName=queue_name)
        return mock_queue["QueueUrl"]

    def _get_role_name(self):
        with mock_iam():
            iam = boto3.client("iam", region_name="eu-west-2")
            try:
                return iam.get_role(RoleName="my-role")["Role"]["Arn"]
            except ClientError:
                return iam.create_role(
                    RoleName="my-role",
                    AssumeRolePolicyDocument="some policy",
                    Path="/my-path/",
                )["Role"]["Arn"]
