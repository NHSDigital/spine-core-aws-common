import unittest

from spine_aws_common import LambdaApplication


class TestLambdaApplication(unittest.TestCase):
    """Testing Lambda application"""

    def setUp(self):
        pass

    def test_lambda(self):
        response = LambdaApplication()
        response_mock = {"message": "Lambda application stopped"}
        self.assertEqual(response_mock, response)
