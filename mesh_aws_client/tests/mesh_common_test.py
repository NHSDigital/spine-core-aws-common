"""Tests for MeshMailbox class (mesh_client wrapper)"""
from unittest import TestCase, mock
import json
import os

from moto import mock_ssm
import boto3
import requests_mock

from mesh_aws_client.mesh_common import MeshMailbox
from mesh_aws_client.tests.mesh_testing_common import MeshTestingCommon
from spine_aws_common.tests.utils.log_helper import LogHelper


class TestMeshMailbox(TestCase):
    """Testing MeshMailbox class"""

    def __init__(self, method_name):
        super().__init__(methodName=method_name)
        self.environment = None
        self.ssm_client = None

    @mock_ssm
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
        self.environment = os.environ["ENV"]
        self.ssm_client = boto3.client("ssm", region_name="eu-west-2")

    def tearDown(self):
        self.log_helper.clean_up()

    @mock_ssm
    @requests_mock.Mocker()
    def test_mesh_mailbox(self, mock_response):
        """Test mailbox functionality"""

        mock_response.post(
            "/messageexchange/MESH-TEST2", text=json.dumps({"mailboxId": "MESH-TEST2"})
        )
        mock_response.get(
            "/messageexchange/MESH-TEST2/inbox", text=json.dumps({"messages": []})
        )

        MeshTestingCommon.setup_mock_aws_ssm_parameter_store(
            self.environment, self.ssm_client
        )

        mailbox = MeshMailbox(mock.MagicMock(), "MESH-TEST2", self.environment)
        response = mailbox.authenticate()
        self.assertEqual(response, b"hello")
        response = mailbox.mesh_client.list_messages()
        self.assertTrue(isinstance(response, list))
