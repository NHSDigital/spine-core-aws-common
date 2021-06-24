from unittest import mock, TestCase
from spine_aws_common import LambdaApplication


class TestLambdaApplication(TestCase):
    """Testing Lambda application"""

    def setUp(self):
        pass

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
        response = LambdaApplication().main(event=event, context=None)
        response_mock = {"message": "Lambda application stopped"}
        self.assertEqual(response_mock, response)

    def test_lambda_additional_logging(self):
        app = LambdaApplication(
            additional_log_config="/home/spineii-user/spine-core-aws-common/tests/unit/add_config.cfg"
        )
        app.log_object.write_log(
            "ADDTEST001",
            None,
            None,
        )
        self.assertLogs("ADDTEST001", level="INFO")
