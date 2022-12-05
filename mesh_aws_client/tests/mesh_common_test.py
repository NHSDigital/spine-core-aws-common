"""Tests for MeshMailbox class (mesh_client wrapper)"""
from unittest import TestCase, mock
import os

from moto import mock_ssm, mock_secretsmanager
import boto3

from mesh_aws_client.mesh_common import MeshCommon
from spine_aws_common.log.log_helper import LogHelper


class TestMeshCommon(TestCase):
    """Testing MeshCommon class"""

    def __init__(self, method_name):
        super().__init__(methodName=method_name)
        self.environment = None
        self.ssm_client = None
        self.secrets_manager = None

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
        self.secrets_manager = boto3.client("secretsmanager", region_name="eu-west-2")

    def tearDown(self):
        self.log_helper.clean_up()

    @mock_ssm
    @mock_secretsmanager
    def test_get_params_ssm_and_secrets(self):
        """
        Test get_params will get both ssm variables and secrets
        when use_secrets_manager is true
        """
        os.environ["use_secrets_manager"] = "true"
        self.secrets_manager.create_secret(
            Name=f"/{self.environment}/mesh/MESH_CLIENT_KEY",
            Description=f"/{self.environment}/mesh/MESH_CLIENT_KEY",
            SecretString="DummyKey1",
        )
        self.secrets_manager.create_secret(
            Name=f"/{self.environment}/mesh/MESH_CLIENT_KEY2",
            Description=f"/{self.environment}/mesh/MESH_CLIENT_KEY2",
            SecretString="DummyKey2",
        )
        self.secrets_manager.create_secret(
            Name=f"/{self.environment}/foobar/FOOBAR_KEY1",
            Description=f"/{self.environment}/foobar/FOOBAR_KEY1",
            SecretString="FoobarKey2",
        )
        self.ssm_client.put_parameter(
            Name=f"/{self.environment}/mesh/MESH_URL1",
            Description=f"/{self.environment}/mesh/MESH_URL1",
            Overwrite=True,
            Type="String",
            Value="DummyUrl1",
        )
        self.ssm_client.put_parameter(
            Name=f"/{self.environment}/mesh/MESH_URL2",
            Description=f"/{self.environment}/mesh/MESH_URL2",
            Overwrite=True,
            Type="String",
            Value="DummyUrl2",
        )
        self.ssm_client.put_parameter(
            Name=f"/{self.environment}/foobar/FOOBAR_URL",
            Description=f"/{self.environment}/foobar/FOOBAR_URL",
            Overwrite=True,
            Type="String",
            Value="FoobarUrl1",
        )
        param_dict = MeshCommon.get_params(f"/{self.environment}/mesh/")
        expected_params = {
            "MESH_URL1": "DummyUrl1",
            "MESH_URL2": "DummyUrl2",
            "MESH_CLIENT_KEY": "DummyKey1",
            "MESH_CLIENT_KEY2": "DummyKey2",
        }
        self.assertEqual(expected_params, param_dict)
        os.environ["use_secrets_manager"] = ""

    @mock_ssm
    @mock_secretsmanager
    def test_get_params_just_ssm(self):
        """
        Test get_params will only get ssm variables when
        use_secrets_manager is false
        """
        os.environ["use_secrets_manager"] = "false"
        self.secrets_manager.create_secret(
            Name=f"/{self.environment}/mesh/MESH_CLIENT_KEY",
            Description=f"/{self.environment}/mesh/MESH_CLIENT_KEY",
            SecretString="DummyKey1",
        )
        self.secrets_manager.create_secret(
            Name=f"/{self.environment}/mesh/MESH_CLIENT_KEY2",
            Description=f"/{self.environment}/mesh/MESH_CLIENT_KEY2",
            SecretString="DummyKey2",
        )
        self.secrets_manager.create_secret(
            Name=f"/{self.environment}/foobar/FOOBAR_KEY1",
            Description=f"/{self.environment}/foobar/FOOBAR_KEY1",
            SecretString="FoobarKey2",
        )
        self.ssm_client.put_parameter(
            Name=f"/{self.environment}/mesh/MESH_URL1",
            Description=f"/{self.environment}/mesh/MESH_URL1",
            Overwrite=True,
            Type="String",
            Value="DummyUrl1",
        )
        self.ssm_client.put_parameter(
            Name=f"/{self.environment}/mesh/MESH_URL2",
            Description=f"/{self.environment}/mesh/MESH_URL2",
            Overwrite=True,
            Type="String",
            Value="DummyUrl2",
        )
        self.ssm_client.put_parameter(
            Name=f"/{self.environment}/foobar/FOOBAR_URL",
            Description=f"/{self.environment}/foobar/FOOBAR_URL",
            Overwrite=True,
            Type="String",
            Value="FoobarUrl1",
        )
        param_dict = MeshCommon.get_params(f"/{self.environment}/mesh/")
        expected_params = {"MESH_URL1": "DummyUrl1", "MESH_URL2": "DummyUrl2"}
        self.assertEqual(expected_params, param_dict)
