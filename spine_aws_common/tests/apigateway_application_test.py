"""
API Gateway Testing
"""
import json
from os.path import dirname
from unittest import mock, TestCase

from aws_lambda_powertools.event_handler.api_gateway import Response
from spine_aws_common import APIGatewayApplication
from spine_aws_common.tests.utils.log_helper import LogHelper


class MyApp(APIGatewayApplication):
    """Test App"""

    @staticmethod
    def get_hello():
        """Get hello"""
        return Response(
            status_code=200, content_type="application/json", body='{"hello":"world"}'
        )

    @staticmethod
    def get_id(_id):
        """Get id"""
        response_dict = {"id": _id}
        return Response(
            status_code=200,
            content_type="application/json",
            body=json.dumps(response_dict),
        )

    def configure_routes(self):
        """Configure routes"""
        self._add_route(self.get_hello, "/hello")
        self._add_route(self.get_id, "/id/<_id>")


class TestAPIGatewayApplication(TestCase):
    """Testing Lambda application"""

    def setUp(self):
        self.log_helper = LogHelper()
        self.log_helper.set_stdout_capture()

    def tearDown(self):
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
        """Testing lambda"""
        with open(f"{dirname(__file__)}/testdata/apigateway_hello.json") as _file:
            event = json.load(_file)

        response = MyApp().main(event, {})
        expected_response = {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": '{"hello":"world"}',
            "isBase64Encoded": False,
        }
        self.assertEqual(response, expected_response)

    def test_id(self):
        """Testing get id"""
        with open(f"{dirname(__file__)}/testdata/apigateway_id.json") as _file:
            event = json.load(_file)

        response = MyApp().main(event, {})
        expected_response = {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": '{"id": "12345"}',
            "isBase64Encoded": False,
        }
        self.assertEqual(response, expected_response)

    def test_header_retrieval_case_insensitive(self):
        """Testing that retrieval of headers is case insensitive"""
        with open(f"{dirname(__file__)}/testdata/apigateway_hello.json") as _file:
            event = json.load(_file)

        internal_id = "1234"
        event["headers"]["X-Internal-Id"] = internal_id

        response = MyApp().main(event, {})
        expected_response = {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": '{"hello":"world"}',
            "isBase64Encoded": False,
        }
        self.assertEqual(response, expected_response)
        self.assertTrue(
            self.log_helper.was_value_logged("LAMBDA0002", "internalID", internal_id)
        )
