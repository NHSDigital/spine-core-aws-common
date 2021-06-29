# pylint:disable=protected-access
"""
Lambda Testing
"""
from unittest import mock, TestCase
from aws_lambda_powertools.utilities.typing.lambda_context import LambdaContext

from spine_aws_common.tests.utils.log_helper import LogHelper
from spine_aws_common import LambdaApplication


class TestLambdaApplication(TestCase):
    """Testing Lambda application"""

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
