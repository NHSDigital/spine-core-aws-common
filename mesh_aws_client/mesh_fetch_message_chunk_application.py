"""
Module for MESH API functionality for step functions
"""
from http import HTTPStatus
import os
import json

import boto3
from botocore.errorfactory import ClientError

from spine_aws_common import LambdaApplication
from mesh_aws_client.mesh_common import AwsFailedToPerformError, MeshCommon
from mesh_aws_client.mesh_mailbox import MeshMailbox


class MeshFetchMessageChunkApplication(
    LambdaApplication
):  # pylint: disable=too-many-instance-attributes
    """
    MESH API Lambda for sending a message
    """

    MEBIBYTE = 1024 * 1024
    DEFAULT_BUFFER_SIZE = 5 * MEBIBYTE

    def __init__(self, additional_log_config=None, load_ssm_params=False):
        """
        Init variables
        """
        super().__init__(additional_log_config, load_ssm_params)
        self.mailbox = None
        self.input = {}
        self.environment = os.environ.get("Environment", "default")
        self.chunk_size = os.environ.get("CHUNK_SIZE", MeshCommon.DEFAULT_CHUNK_SIZE)
        self.http_response = None
        self.response = {}
        self.internal_id = None
        self.aws_upload_id = None
        self.aws_current_part_id = 1
        self.aws_part_etags = []
        self.chunked = False
        self.current_chunk = 1
        self.message_id = None
        self.region = os.environ.get("AWS_REGION", "eu-west-2")
        self.s3_client = None
        self.s3_bucket = ""
        self.s3_key = ""

    def initialise(self):
        """decode input event"""
        self.input = self.event.get("body")
        self.internal_id = self.input.get("internal_id", "Not Provided")
        self.aws_upload_id = self.input.get("aws_upload_id", None)
        self.aws_current_part_id = self.input.get("aws_current_part_id", 1)
        self.aws_part_etags = self.input.get("aws_part_etags", [])
        self.chunked = self.input.get("chunked")
        self.current_chunk = self.input.get("chunk_num", 1)
        self.message_id = self.input["message_id"]
        self.response = self.event.raw_event

    def _setup_mailbox(self):
        self.mailbox = MeshMailbox(
            self.log_object, self.input["dest_mailbox"], self.environment
        )

    def _get_filename(self):
        file_name = self.http_response.headers.get("Mex-Filename", "")
        if len(file_name) == 0:
            if self.http_response.headers.get("Mex-Messagetype") == "REPORT":
                file_name = self.message_id + ".ctl"
            else:
                file_name = self.message_id + ".dat"
        return file_name

    def _get_aws_bucket_and_key(self):
        self.s3_bucket = self.mailbox.params["INBOUND_BUCKET"]
        s3_folder = self.mailbox.params.get("INBOUND_FOLDER", "")
        if len(s3_folder) > 0:
            s3_folder += "/"
        file_name = self._get_filename()
        self.s3_key = s3_folder + (
            file_name if len(file_name) > 0 else self.message_id + ".dat"
        )

    def _is_last_chunk(self, chunk_num):
        chunk_range = self.http_response.headers.get("Mex-Chunk-Range", "1:1")
        number_of_chunks = int(chunk_range.split(":")[1])
        last_chunk = chunk_num == number_of_chunks
        return last_chunk

    def _upload_part_to_s3(self, buffer, last_chunk):
        """Upload a part to S3 and check response"""

        # check if part_overflow_{message_id}.tmp exists and pre-pend to buffer
        filename = f"part_overflow_{self.message_id}.tmp"
        s3_tempfile_key = os.path.basename(self.s3_key) + filename
        try:
            s3_response = self.s3_client.get_object(
                Bucket=self.s3_bucket, Key=s3_tempfile_key
            )
            if s3_response["ResponseMetadata"]["HTTPStatusCode"] == HTTPStatus.OK.value:
                pre_buffer = s3_response["Body"].read()
                buffer = pre_buffer + buffer
                self.log_object.write_log(
                    "MESHFETCH0002b",
                    None,
                    {
                        "aws_part_size": len(pre_buffer),
                        "aws_upload_id": self.aws_upload_id,
                    },
                )
            self.s3_client.delete_object(
                Bucket=self.s3_bucket,
                Key=s3_tempfile_key,
                BypassGovernanceRetention=True,
            )
        except ClientError:
            # Not found
            pass

        if not last_chunk:  # not on last chunk
            if len(buffer) < 5 * self.MEBIBYTE:
                # write to s3 if buffer is less than 5 MebiBytes and last part of chunk
                self.s3_client.put_object(
                    Bucket=self.s3_bucket,
                    Key=s3_tempfile_key,
                    Body=buffer,
                )
                self.log_object.write_log(
                    "MESHFETCH0002a",
                    None,
                    {
                        "aws_part_size": len(buffer),
                        "aws_upload_id": self.aws_upload_id,
                    },
                )
                return None

        response = self.s3_client.upload_part(
            Body=buffer,
            Bucket=self.s3_bucket,
            Key=self.s3_key,
            PartNumber=self.aws_current_part_id,
            ContentLength=len(buffer),
            UploadId=self.aws_upload_id,
        )
        # check return code
        if response["ResponseMetadata"].get("HTTPStatusCode") != HTTPStatus.OK.value:
            self.response.update({"statusCode": HTTPStatus.INTERNAL_SERVER_ERROR.value})
            # logpoint
            raise AwsFailedToPerformError(
                f'Failed to partial upload key="{self.s3_key}" into'
                + f' bucket="{self.s3_bucket}"'
                + f' part_id="{self.aws_current_part_id}" to save from MESH'
            )
        etag = response["ETag"]
        self.aws_part_etags.append(
            {
                "ETag": etag,
                "PartNumber": self.aws_current_part_id,
            }
        )
        self.aws_current_part_id += 1
        self.log_object.write_log(
            "MESHFETCH0002",
            None,
            {
                "aws_part_id": self.aws_current_part_id,
                "aws_part_size": len(buffer),
                "aws_upload_id": self.aws_upload_id,
                "etag": etag,
            },
        )
        return etag

    def _create_multipart_upload(self):
        """Create an S3 multipart upload"""
        multipart_upload = self.s3_client.create_multipart_upload(
            Bucket=self.s3_bucket,
            Key=self.s3_key,
        )
        self.aws_upload_id = multipart_upload["UploadId"]
        # check return code
        if (
            multipart_upload["ResponseMetadata"].get("HTTPStatusCode")
            != HTTPStatus.OK.value
        ):
            self.response.update({"statusCode": HTTPStatus.INTERNAL_SERVER_ERROR.value})
            # logpoint
            raise AwsFailedToPerformError(
                f'Failed to create multi-part upload key="{self.s3_key}" into '
                + f'bucket="{self.s3_bucket}"'
                + f' aws_upload_id="{self.aws_upload_id}" to save from MESH'
            )

    def _finish_multipart_upload(self):
        """Complete the s3 multipart upload"""
        response = self.s3_client.complete_multipart_upload(
            Bucket=self.s3_bucket,
            Key=self.s3_key,
            UploadId=self.aws_upload_id,
            MultipartUpload={"Parts": self.aws_part_etags},
        )
        # check return code
        if response["ResponseMetadata"].get("HTTPStatusCode") != HTTPStatus.OK.value:
            self.response.update({"statusCode": HTTPStatus.INTERNAL_SERVER_ERROR.value})
            # logpoint
            raise AwsFailedToPerformError(
                f'Failed to complete multi-part upload key="{self.s3_key}"'
                + f'into bucket="{self.s3_bucket}"'
                + f' aws_upload_id="{self.aws_upload_id}" to save from MESH'
            )

    def start(self):
        """
        Main body of lambda function
        """
        self.s3_client = boto3.client("s3", region_name=self.region)

        self.log_object.internal_id = self.internal_id
        self._setup_mailbox()

        self.log_object.write_log(
            "MESHFETCH0001",
            None,
            {
                "message_id": self.message_id,
            },
        )

        # get stream for this chunk
        self.http_response = self.mailbox.get_chunk(
            self.message_id, chunk_num=self.current_chunk
        )
        self.http_response.raise_for_status()
        self.chunked = (
            self.http_response.status_code == HTTPStatus.PARTIAL_CONTENT.value
        )

        # get s3 bucket and key
        self._get_aws_bucket_and_key()

        if self.current_chunk == 1:
            # create multipart upload even if only one chunk
            self._create_multipart_upload()

        parts_read = 0
        part_buffer = b""
        bytes_read = 0

        is_report = self.http_response.headers.get("Mex-Messagetype") == "REPORT"
        if is_report:
            buffer = json.dumps(dict(self.http_response.headers))
            self._upload_part_to_s3(buffer, True)
            bytes_read = len(buffer)
        else:
            # read bytes into buffer
            for buffer in self.http_response.iter_content(
                chunk_size=self.DEFAULT_BUFFER_SIZE
            ):
                parts_read += 1
                last_chunk = self._is_last_chunk(self.current_chunk)
                etag = self._upload_part_to_s3(
                    part_buffer + buffer, last_chunk
                )
                if etag:
                    part_buffer = b""
                else:
                    part_buffer = buffer
                    bytes_read += len(buffer)

        self.log_object.write_log(
            "MESHFETCH0001a",
            None,
            {
                "length": bytes_read,
                "message_id": self.message_id,
            },
        )

        is_finished = not self.chunked
        if is_finished:
            self._finish_multipart_upload()
            self.log_object.write_log(
                "MESHFETCH0004", None, {"message_id": self.message_id}
            )
            self.mailbox.acknowledge_message(self.message_id)
        else:
            self.log_object.write_log(
                "MESHFETCH0003",
                None,
                {"chunk": self.current_chunk, "message_id": self.message_id},
            )
            self.current_chunk += 1

        # update event to send as response
        self.response.update({"statusCode": self.http_response.status_code})
        self.response["body"].update(
            {
                "complete": is_finished,
                "chunk_num": self.current_chunk,
                "aws_upload_id": self.aws_upload_id,
                "aws_current_part_id": self.aws_current_part_id,
                "aws_part_etags": self.aws_part_etags,
                "internal_id": self.internal_id,
                "file_name": self._get_filename(),
            }
        )
        self.mailbox.clean_up()


# create instance of class in global space
# this ensures initial setup of logging/config is only done on cold start
app = MeshFetchMessageChunkApplication()


def lambda_handler(event, context):
    """Standard lambda_handler"""
    return app.main(event, context)
