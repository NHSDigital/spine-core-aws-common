""" Testing MeshFetchMessageChunk Application """
import json
from http import HTTPStatus
from unittest import mock

import boto3
import requests_mock
from moto import mock_s3, mock_ssm
from parameterized import parameterized
from requests.exceptions import HTTPError

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
        self, mock_create_new_internal_id, response_mocker
    ):
        """Test the lambda with small file, no chunking, happy path"""
        # Mock responses from MESH server
        response_mocker.get(
            f"/messageexchange/MESH-TEST1/inbox/{MeshTestingCommon.KNOWN_MESSAGE_ID1}",
            text="123456789012345678901234567890123",
            status_code=HTTPStatus.OK.value,
            headers={
                "Content-Type": "application/octet-stream",
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
        response_mocker.put(
            f"/messageexchange/MESH-TEST1/inbox/{MeshTestingCommon.KNOWN_MESSAGE_ID1}"
            + "/status/acknowledged",
            text=json.dumps({"messageId": MeshTestingCommon.KNOWN_MESSAGE_ID1}),
            headers={
                "Content-Type": "application/json",
                "Transfer-Encoding": "chunked",
                "Connection": "keep-alive",
            },
        )

        mock_create_new_internal_id.return_value = MeshTestingCommon.KNOWN_INTERNAL_ID1
        s3_client = boto3.client("s3", region_name="eu-west-2")
        ssm_client = boto3.client("ssm", region_name="eu-west-2")
        MeshTestingCommon.setup_mock_aws_s3_buckets(self.environment, s3_client)
        MeshTestingCommon.setup_mock_aws_ssm_parameter_store(
            self.environment, ssm_client
        )
        mock_input = self._sample_first_input_event()

        try:
            response = self.app.main(
                event=mock_input, context=MeshTestingCommon.CONTEXT
            )
        except Exception as exception:  # pylint: disable=broad-except
            # need to fail happy pass on any exception
            self.fail(f"Invocation crashed with Exception {str(exception)}")

        # print(response)

        self.assertEqual(
            mock_input["body"].get("internal_id"), response["body"].get("internal_id")
        )
        self.assertEqual(
            response["body"].get("internal_id"),
            MeshTestingCommon.KNOWN_INTERNAL_ID1,
        )
        # Some checks on the response body
        self.assertEqual(response["body"].get("complete"), True)
        self.assertIn("aws_current_part_id", response["body"])
        self.assertIn("aws_upload_id", response["body"])

        # Should be 0 etags uploaded to S3 as multipart not used on single chunk
        self.assertEqual(len(response["body"].get("aws_part_etags")), 0)

        # Check we got the logs we expect
        self.assertTrue(
            self.log_helper.was_value_logged("MESHFETCH0001", "Log_Level", "INFO")
        )
        self.assertTrue(
            self.log_helper.was_value_logged("MESHFETCH0001c", "Log_Level", "INFO")
        )
        self.assertTrue(
            self.log_helper.was_value_logged("MESHFETCH0002a", "Log_Level", "INFO")
        )
        self.assertFalse(
            self.log_helper.was_value_logged("MESHFETCH0003", "Log_Level", "INFO")
        )
        self.assertTrue(
            self.log_helper.was_value_logged("MESHFETCH0011", "Log_Level", "INFO")
        )
        # self.assertTrue(
        #     self.log_helper.was_value_logged("MESHFETCH0005a", "Log_Level", "INFO")
        # )
        # self.assertFalse(
        #     self.log_helper.was_value_logged("MESHFETCH0008", "Log_Level", "INFO")
        # )
        self.assertFalse(
            self.log_helper.was_value_logged("MESHFETCH0010a", "Log_Level", "INFO")
        )
        self.assertTrue(
            self.log_helper.was_value_logged("LAMBDA0003", "Log_Level", "INFO")
        )

    @parameterized.expand([("_happy_path", 20), ("odd_sized_chunk_with_temp_file", 18)])
    @mock_ssm
    @mock_s3
    @mock.patch.object(MeshFetchMessageChunkApplication, "_create_new_internal_id")
    @requests_mock.Mocker()
    def test_mesh_fetch_file_chunk_app_2_chunks(
        self,
        _,
        mock_data1_length,
        mock_create_new_internal_id,
        mock_response,
    ):
        """
        Test that doing chunking works
        """
        mebibyte = 1024 * 1024
        # Create some test data
        data1_length = mock_data1_length * mebibyte  # 20 MiB
        data1 = ""
        while len(data1) < data1_length:
            data1 += "1234567890"
        data1_length = len(data1)
        data2_length = 4 * mebibyte  # 4 MiB
        data2 = ""
        while len(data2) < data2_length:
            data2 += "1234567890"
        data2_length = len(data2)

        # Mock responses from MESH server TODO refactor!
        mock_response.get(
            f"/messageexchange/MESH-TEST1/inbox/{MeshTestingCommon.KNOWN_MESSAGE_ID1}",
            text=data1,
            status_code=HTTPStatus.PARTIAL_CONTENT.value,
            headers={
                "Content-Type": "application/octet-stream",
                "Connection": "keep-alive",
                "Mex-Chunk-Range": "1:2",
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
        # next chunk http response
        mock_response.get(
            "/messageexchange/MESH-TEST1/inbox/"
            + f"{MeshTestingCommon.KNOWN_MESSAGE_ID1}/2",
            text=data2,
            status_code=HTTPStatus.OK.value,
            headers={
                "Content-Type": "application/octet-stream",
                "Mex-Chunk-Range": "2:2",
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

        mock_create_new_internal_id.return_value = MeshTestingCommon.KNOWN_INTERNAL_ID1

        s3_client = boto3.client("s3", config=MeshTestingCommon.aws_config)
        ssm_client = boto3.client("ssm", config=MeshTestingCommon.aws_config)
        MeshTestingCommon.setup_mock_aws_s3_buckets(self.environment, s3_client)
        MeshTestingCommon.setup_mock_aws_ssm_parameter_store(
            self.environment, ssm_client
        )
        mock_input = self._sample_first_input_event()

        try:
            response = self.app.main(
                event=mock_input, context=MeshTestingCommon.CONTEXT
            )
        except Exception as exception:  # pylint: disable=broad-except
            # need to fail happy pass on any exception
            self.fail(f"Invocation crashed with Exception {str(exception)}")

        expected_return_code = HTTPStatus.PARTIAL_CONTENT.value
        self.assertEqual(response["statusCode"], expected_return_code)
        self.assertEqual(response["body"]["chunk_num"], 2)
        self.assertEqual(response["body"]["complete"], False)

        # feed response into next lambda invocation
        mock_input = response

        try:
            response = self.app.main(
                event=mock_input, context=MeshTestingCommon.CONTEXT
            )
        except Exception as exception:  # pylint: disable=broad-except
            # need to fail happy pass on any exception
            self.fail(f"Invocation crashed with Exception {str(exception)}")

        expected_return_code = HTTPStatus.OK.value
        self.assertEqual(response["statusCode"], expected_return_code)
        self.assertEqual(response["body"]["complete"], True)

        # Check we got the logs we expect
        self.assertTrue(
            self.log_helper.was_value_logged("MESHFETCH0001", "Log_Level", "INFO")
        )
        self.assertTrue(
            self.log_helper.was_value_logged("MESHFETCH0001c", "Log_Level", "INFO")
        )
        self.assertTrue(
            self.log_helper.was_value_logged("MESHFETCH0002", "Log_Level", "INFO")
        )
        self.assertTrue(
            self.log_helper.was_value_logged("MESHFETCH0003", "Log_Level", "INFO")
        )
        self.assertTrue(
            self.log_helper.was_value_logged("MESHFETCH0004", "Log_Level", "INFO")
        )
        # self.assertTrue(
        #     self.log_helper.was_value_logged("MESHFETCH0005a", "Log_Level", "INFO")
        # )
        # self.assertFalse(
        #     self.log_helper.was_value_logged("MESHFETCH0008", "Log_Level", "INFO")
        # )
        self.assertTrue(
            self.log_helper.was_value_logged("LAMBDA0003", "Log_Level", "INFO")
        )

    @mock_ssm
    @mock_s3
    @mock.patch.object(MeshFetchMessageChunkApplication, "_create_new_internal_id")
    @requests_mock.Mocker()
    def test_mesh_fetch_file_chunk_app_2_chunks_using_temp_file(
        self, mock_create_new_internal_id, mock_response
    ):
        """
        Test that doing chunking works with temp file
        """
        mebibyte = 1024 * 1024
        # Create some test data
        data1_length = 18 * mebibyte  # 20 MiB
        data1 = ""
        while len(data1) < data1_length:
            data1 += "1234567890"
        data1_length = len(data1)
        data2_length = 4 * mebibyte  # 4 MiB
        data2 = ""
        while len(data2) < data2_length:
            data2 += "1234567890"
        data2_length = len(data2)

        # Mock responses from MESH server TODO refactor!
        mock_response.get(
            f"/messageexchange/MESH-TEST1/inbox/{MeshTestingCommon.KNOWN_MESSAGE_ID1}",
            text=data1,
            status_code=HTTPStatus.PARTIAL_CONTENT.value,
            headers={
                "Content-Type": "application/octet-stream",
                "Connection": "keep-alive",
                "Mex-Chunk-Range": "1:2",
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
        # next chunk http response
        mock_response.get(
            "/messageexchange/MESH-TEST1/inbox/"
            + f"{MeshTestingCommon.KNOWN_MESSAGE_ID1}/2",
            text=data2,
            status_code=HTTPStatus.OK.value,
            headers={
                "Content-Type": "application/octet-stream",
                "Mex-Chunk-Range": "2:2",
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

        mock_create_new_internal_id.return_value = MeshTestingCommon.KNOWN_INTERNAL_ID1

        s3_client = boto3.client("s3", config=MeshTestingCommon.aws_config)
        ssm_client = boto3.client("ssm", config=MeshTestingCommon.aws_config)
        MeshTestingCommon.setup_mock_aws_s3_buckets(self.environment, s3_client)
        MeshTestingCommon.setup_mock_aws_ssm_parameter_store(
            self.environment, ssm_client
        )
        mock_input = self._sample_first_input_event()

        try:
            response = self.app.main(
                event=mock_input, context=MeshTestingCommon.CONTEXT
            )
        except Exception as exception:  # pylint: disable=broad-except
            # need to fail happy pass on any exception
            self.fail(f"Invocation crashed with Exception {str(exception)}")

        expected_return_code = HTTPStatus.PARTIAL_CONTENT.value
        self.assertEqual(response["statusCode"], expected_return_code)
        self.assertEqual(response["body"]["chunk_num"], 2)
        self.assertEqual(response["body"]["complete"], False)

        # feed response into next lambda invocation
        mock_input = response

        try:
            response = self.app.main(
                event=mock_input, context=MeshTestingCommon.CONTEXT
            )
        except Exception as exception:  # pylint: disable=broad-except
            # need to fail happy pass on any exception
            self.fail(f"Invocation crashed with Exception {str(exception)}")

        expected_return_code = HTTPStatus.OK.value
        self.assertEqual(response["statusCode"], expected_return_code)
        self.assertEqual(response["body"]["complete"], True)

        # Check we got the logs we expect
        self.assertTrue(
            self.log_helper.was_value_logged("MESHFETCH0001", "Log_Level", "INFO")
        )
        self.assertTrue(
            self.log_helper.was_value_logged("MESHFETCH0001c", "Log_Level", "INFO")
        )
        self.assertTrue(
            self.log_helper.was_value_logged("MESHFETCH0002", "Log_Level", "INFO")
        )
        self.assertTrue(
            self.log_helper.was_value_logged("MESHFETCH0002a", "Log_Level", "INFO")
        )
        self.assertTrue(
            self.log_helper.was_value_logged("MESHFETCH0003", "Log_Level", "INFO")
        )
        self.assertTrue(
            self.log_helper.was_value_logged("MESHFETCH0004", "Log_Level", "INFO")
        )
        self.assertTrue(
            self.log_helper.was_value_logged("MESHFETCH0005a", "Log_Level", "INFO")
        )
        self.assertFalse(
            self.log_helper.was_value_logged("MESHFETCH0010a", "Log_Level", "INFO")
        )
        self.assertTrue(
            self.log_helper.was_value_logged("LAMBDA0003", "Log_Level", "INFO")
        )

    @mock_ssm
    @mock_s3
    @mock.patch.object(MeshFetchMessageChunkApplication, "_create_new_internal_id")
    @requests_mock.Mocker()
    def test_mesh_fetch_file_chunk_app_report(
        self, mock_create_new_internal_id, response_mocker
    ):
        """Test the lambda with a Non-Delivery Report"""
        # Mock responses from MESH server
        response_mocker.get(
            f"/messageexchange/MESH-TEST1/inbox/{MeshTestingCommon.KNOWN_MESSAGE_ID1}",
            text="",
            status_code=HTTPStatus.OK.value,
            headers={
                "Content-Type": "application/octet-stream",
                "Connection": "keep-alive",
                "Mex-Messageid": MeshTestingCommon.KNOWN_MESSAGE_ID2,
                "Mex-Linkedmsgid": MeshTestingCommon.KNOWN_MESSAGE_ID1,
                "Mex-To": "MESH-TEST1",
                "Mex-Subject": "NDR",
                "Mex-Workflowid": "TESTWORKFLOW",
                "Mex-Messagetype": "REPORT",
                "Mex-Version": "1.0",
                "Mex-Addresstype": "ALL",
                "Mex-Statuscode": "14",
                "Mex-Statusevent": "SEND",
                "Mex-Statusdescription": "Message not collected by recipient after 5 days",  # noqa pylint: disable=line-too-long
                "Mex-Statussuccess": "ERROR",
                "Mex-Statustimestamp": "20210705162157",
                "Mex-Content-Compressed": "N",
                "Etag": "915cd12d58ce2f820959e9ba41b2ebb02f2e6005",
                "Strict-Transport-Security": "max-age=15552000",
            },
        )
        response_mocker.put(
            f"/messageexchange/MESH-TEST1/inbox/{MeshTestingCommon.KNOWN_MESSAGE_ID1}"
            + "/status/acknowledged",
            text=json.dumps({"messageId": MeshTestingCommon.KNOWN_MESSAGE_ID1}),
            headers={
                "Content-Type": "application/json",
                "Transfer-Encoding": "chunked",
                "Connection": "keep-alive",
            },
        )
        mock_create_new_internal_id.return_value = MeshTestingCommon.KNOWN_INTERNAL_ID1
        s3_client = boto3.client("s3", region_name="eu-west-2")
        ssm_client = boto3.client("ssm", region_name="eu-west-2")
        MeshTestingCommon.setup_mock_aws_s3_buckets(self.environment, s3_client)
        MeshTestingCommon.setup_mock_aws_ssm_parameter_store(
            self.environment, ssm_client
        )
        mock_input = self._sample_first_input_event()
        try:
            response = self.app.main(
                event=mock_input, context=MeshTestingCommon.CONTEXT
            )
        except Exception as exception:  # pylint: disable=broad-except
            # need to fail happy pass on any exception
            self.fail(f"Invocation crashed with Exception {str(exception)}")

        expected_return_code = HTTPStatus.OK.value
        self.assertEqual(response["statusCode"], expected_return_code)
        # self.assertTrue(
        #     self.log_helper.was_value_logged("MESHFETCH0008", "Log_Level", "INFO")
        # )

        self.assertTrue(
            self.log_helper.was_value_logged("MESHFETCH0012", "Log_Level", "INFO")
        )

    @mock_ssm
    @mock_s3
    @mock.patch.object(MeshFetchMessageChunkApplication, "_create_new_internal_id")
    @requests_mock.Mocker()
    def test_mesh_fetch_file_chunk_app_gone_away_unhappy_path(
        self, mock_create_new_internal_id, mock_response
    ):
        """Test the lambda with unhappy path"""
        # Mock responses from MESH server
        mock_response.get(
            f"/messageexchange/MESH-TEST1/inbox/{MeshTestingCommon.KNOWN_MESSAGE_ID1}",
            text="",
            status_code=HTTPStatus.GONE.value,
            headers={
                "Content-Type": "application/json",
            },
        )

        mock_create_new_internal_id.return_value = MeshTestingCommon.KNOWN_INTERNAL_ID1
        s3_client = boto3.client("s3", region_name="eu-west-2")
        ssm_client = boto3.client("ssm", region_name="eu-west-2")
        MeshTestingCommon.setup_mock_aws_s3_buckets(self.environment, s3_client)
        MeshTestingCommon.setup_mock_aws_ssm_parameter_store(
            self.environment, ssm_client
        )
        mock_input = self._sample_first_input_event()

        try:
            self.app.main(event=mock_input, context=MeshTestingCommon.CONTEXT)
        except HTTPError:
            return
        self.fail("Failed to raise 410 Client Error")

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
