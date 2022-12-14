""" Testing MeshPollMailbox application """

import json
from http import HTTPStatus
from unittest import mock

import boto3
import requests_mock
from moto import mock_s3, mock_ssm, mock_stepfunctions, mock_secretsmanager

from mesh_aws_client.mesh_poll_mailbox_application import (
    MeshPollMailboxApplication,
)
from mesh_aws_client.tests.mesh_testing_common import (
    MeshTestCase,
    MeshTestingCommon,
)


class TestMeshPollMailboxApplication(MeshTestCase):
    """Testing MeshPollMailbox application"""

    @mock.patch.dict("os.environ", MeshTestingCommon.os_environ_values)
    def setUp(self):
        """Override setup to use correct application object"""
        super().setUp()
        self.app = MeshPollMailboxApplication()
        self.environment = self.app.system_config["Environment"]

    @mock_secretsmanager
    @mock_ssm
    @mock_s3
    @mock_stepfunctions
    @requests_mock.Mocker()
    def test_mesh_poll_mailbox_happy_path(self, mock_response):
        """Test the lambda"""

        # Mock response from MESH server
        mock_response.get(
            "/messageexchange/MESH-TEST1/inbox",
            text=json.dumps(
                {
                    "messages": [
                        MeshTestingCommon.KNOWN_MESSAGE_ID1,
                        MeshTestingCommon.KNOWN_MESSAGE_ID2,
                        MeshTestingCommon.KNOWN_MESSAGE_ID3,
                    ]
                }
            ),
        )

        mailbox_name = "MESH-TEST1"
        mock_input = {"mailbox": mailbox_name}
        s3_client = boto3.client("s3", region_name="eu-west-2")
        ssm_client = boto3.client("ssm", region_name="eu-west-2")
        MeshTestingCommon.setup_mock_aws_s3_buckets(self.environment, s3_client)
        MeshTestingCommon.setup_mock_aws_ssm_parameter_store(
            self.environment, ssm_client
        )
        sfn_client = boto3.client("stepfunctions", region_name="eu-west-2")
        response = MeshTestingCommon.setup_step_function(
            sfn_client,
            self.environment,
            self.app.get_messages_step_function_name,
        )
        try:
            response = self.app.main(
                event=mock_input, context=MeshTestingCommon.CONTEXT
            )
        except Exception as e:  # pylint: disable=broad-except
            # need to fail happy pass on any exception
            self.fail(f"Invocation crashed with Exception {str(e)}")

        self.assertEqual(HTTPStatus.OK.value, response["statusCode"])
        # check 3 messages received
        self.assertEqual(3, response["body"]["message_count"])
        # check first message format in message_list
        self.assertEqual(
            MeshTestingCommon.KNOWN_MESSAGE_ID1,
            response["body"]["message_list"][0]["body"]["message_id"],
        )
        self.assertEqual(False, response["body"]["message_list"][0]["body"]["complete"])
        self.assertEqual(
            mailbox_name, response["body"]["message_list"][0]["body"]["dest_mailbox"]
        )
        # check the correct logs exist
        self.assertLogs("LAMBDA0001", level="INFO")
        self.assertLogs("LAMBDA0002", level="INFO")
        self.assertLogs("LAMBDA0003", level="INFO")
        self.assertLogs("MESHPOLL0001", level="INFO")
