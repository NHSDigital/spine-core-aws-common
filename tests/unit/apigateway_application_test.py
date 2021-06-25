from unittest import mock, TestCase
import json
from os.path import dirname
from spine_aws_common import APIGatewayApplication
from aws_lambda_powertools.event_handler.api_gateway import Response


class MyApp(APIGatewayApplication):
    def get_hello(self):
        return Response(
            status_code=200, content_type="application/json", body='{"hello":"world"}'
        )

    def get_id(self, _id):
        response_dict = {"id": _id}
        return Response(
            status_code=200,
            content_type="application/json",
            body=json.dumps(response_dict),
        )

    def initialise(self):
        self.add_route(self.get_hello, "/hello")
        self.add_route(self.get_id, "/id/<_id>")


class TestAPIGatewayApplication(TestCase):
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
        with open(f"{dirname(__file__)}/testdata/apigateway_hello.json") as f:
            event = json.load(f)

        response = MyApp().main(event, {})
        expected_response = {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": '{"hello":"world"}',
            "isBase64Encoded": False,
        }
        self.assertEqual(response, expected_response)

    def test_id(self):
        with open(f"{dirname(__file__)}/testdata/apigateway_id.json") as f:
            event = json.load(f)

        response = MyApp().main(event, {})
        expected_response = {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": '{"id": "12345"}',
            "isBase64Encoded": False,
        }
        self.assertEqual(response, expected_response)
