""" Testing MeshFetchMessageChunk Application """
from http import HTTPStatus
from unittest import mock
import json

from moto import mock_s3, mock_ssm
import boto3
import requests_mock

from mesh_aws_client.mesh_fetch_message_chunk_application import (
    MeshFetchMessageChunkApplication,
)
from mesh_aws_client.tests.mesh_testing_common import (
    MeshTestCase,
    MeshTestingCommon,
)


class TestMeshFetchMessageChunkApplication(MeshTestCase):
    """Testing MeshFetchMessageChunk application"""

    @mock.patch.dict("os.environ", MeshTestingCommon.os_environ_values)
    def setUp(self):
        """Override setup to use correct application object"""
        super().setUp()
        self.app = MeshFetchMessageChunkApplication()
        self.environment = self.app.system_config["Environment"]

    @mock_ssm
    @mock_s3
    @mock.patch.object(MeshFetchMessageChunkApplication, "_create_new_internal_id")
    @requests_mock.Mocker()
    def test_mesh_fetch_file_chunk_app_no_chunks_happy_path(
        self, mock_create_new_internal_id, mock_response
    ):
        """Test the lambda with small file, no chunking, happy path"""
        # Mock responses from MESH server
        mock_response.get(
            f"/messageexchange/MESH-TEST1/inbox/{MeshTestingCommon.KNOWN_MESSAGE_ID1}",
            text="123456789012345678901234567890123",
            headers={
                "Content-Type": "application/octet-stream",
                "Content-Length": "33",
                "Connection": "keep-alive",
                "Mex-Messageid": MeshTestingCommon.KNOWN_MESSAGE_ID1,
                "Mex-From": "MESH-TEST2",
                "Mex-To": "MESH-TEST1",
                "Mex-Fromsmtp": "mesh.automation.testclient2@nhs.org",
                "Mex-Tosmtp": "mesh.automation.testclient1@nhs.org",
                "Mex-Filename": "testfile.txt",
                "Mex-Workflowid": "TESTWORKFLOW",
                "Mex-Messagetype": "DATA",
                "Mex-Version": "1.0",
                "Mex-Addresstype": "ALL",
                "Mex-Statuscode": "00",
                "Mex-Statusevent": "TRANSFER",
                "Mex-Statusdescription": "Transferred to recipient mailbox",
                "Mex-Statussuccess": "SUCCESS",
                "Mex-Statustimestamp": "20210705162157",
                "Mex-Content-Compressed": "N",
                "Etag": "915cd12d58ce2f820959e9ba41b2ebb02f2e6005",
            },
        )
        mock_response.put(
            f"/messageexchange/MESH-TEST1/inbox/{MeshTestingCommon.KNOWN_MESSAGE_ID1}"
            + "/status/acknowledged",
            text=json.dumps({"messageId": MeshTestingCommon.KNOWN_MESSAGE_ID1}),
            headers={
                "Content-Type": "application/json",
                "Transfer-Encoding": "chunked",
                "Connection": "keep-alive",
            },
        )

        mock_create_new_internal_id.return_value = MeshTestingCommon.KNOWN_INTERNAL_ID2
        s3_client = boto3.client("s3", region_name="eu-west-2")
        ssm_client = boto3.client("ssm", region_name="eu-west-2")
        MeshTestingCommon.setup_mock_aws_s3_buckets(self.environment, s3_client)
        MeshTestingCommon.setup_mock_aws_ssm_parameter_store(
            self.environment, ssm_client
        )
        mock_input = self._sample_first_input_event()
        mock_response = self._sample_second_input_event()

        mock_response["body"].update({"complete": True, "chunk_num": 1})
        try:
            response = self.app.main(
                event=mock_input, context=MeshTestingCommon.CONTEXT
            )
        except Exception as e:  # pylint: disable=broad-except
            # need to fail happy pass on any exception
            self.fail(f"Invocation crashed with Exception {str(e)}")

        self.assertNotEqual(
            mock_input.get("internal_id"), response["body"].get("internal_id")
        )
        self.assertEqual(
            response["body"].get("internal_id"),
            mock_response["body"].get("internal_id"),
        )
        self.assertDictEqual(mock_response, response)
        # Check it completed ok
        self.assertTrue(
            self.log_helper.was_value_logged("LAMBDA0003", "Log_Level", "INFO")
        )

    # @mock_ssm
    # @mock_s3
    # def test_mesh_fetch_file_chunk_app_2_chunks_happy_path(self):
    #     """
    #     Test that doing chunking works
    #     """
    #     s3_client = boto3.client("s3")
    #     ssm_client = boto3.client("ssm")
    #     MeshTestingCommon.setup_mock_aws_s3_buckets(self.environment, s3_client)
    #     MeshTestingCommon.setup_mock_aws_ssm_parameter_store(
    #         self.environment, ssm_client
    #     )

    #     response = {"statusCode": HTTPStatus.OK.value}
    #     expected_return_code = {"statusCode": HTTPStatus.OK.value}
    #     self.assertEqual(response, {**response, **expected_return_code})

    @staticmethod
    def _sample_first_input_event():
        return {
            "statusCode": HTTPStatus.OK.value,
            "headers": {"Content-Type": "application/json"},
            "body": {
                "complete": False,
                "internal_id": MeshTestingCommon.KNOWN_INTERNAL_ID1,
                "message_id": MeshTestingCommon.KNOWN_MESSAGE_ID1,
                "dest_mailbox": "MESH-TEST1",
            },
        }

    @staticmethod
    def _sample_second_input_event():
        return {
            "statusCode": HTTPStatus.OK.value,
            "headers": {"Content-Type": "application/json"},
            "body": {
                "complete": False,
                "internal_id": MeshTestingCommon.KNOWN_INTERNAL_ID2,
                "message_id": MeshTestingCommon.KNOWN_MESSAGE_ID1,
                "dest_mailbox": "MESH-TEST1",
                "chunk_num": 2,
                "aws_upload_id": None,
            },
        }
