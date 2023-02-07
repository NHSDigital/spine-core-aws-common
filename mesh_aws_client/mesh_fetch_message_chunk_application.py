"""
Module for MESH API functionality for step functions
"""
from http import HTTPStatus
import os
import json

import boto3
from botocore.exceptions import ClientError

from spine_aws_common import LambdaApplication
from mesh_aws_client.mesh_common import MeshCommon
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
        self.aws_current_part_id = 0
        self.aws_part_etags = []
        self.chunked = False
        self.number_of_chunks = 0
        self.current_chunk = 0
        self.message_id = None
        self.region = os.environ.get("AWS_REGION", "eu-west-2")
        self.s3_client = None
        self.s3_bucket = ""
        self.http_headers_bytes_read = 0
        self.s3_key = ""
        self.s3_tempfile_key = None

    def initialise(self):
        """decode input event"""
        self.input = self.event.get("body")
        self.internal_id = self.input.get("internal_id", "Not Provided")
        self.aws_upload_id = self.input.get("aws_upload_id", "Not Provided")
        self.aws_current_part_id = self.input.get("aws_current_part_id", 1)
        self.aws_part_etags = self.input.get("aws_part_etags", [])
        self.chunked = self.input.get("chunked")
        self.current_chunk = self.input.get("chunk_num", 1)
        self.message_id = self.input["message_id"]
        self.response = self.event.raw_event
        self.s3_client = boto3.client("s3", region_name=self.region)
        self.log_object.internal_id = self.internal_id
        self._setup_mailbox()

    def _setup_mailbox(self):
        self.mailbox = MeshMailbox(
            self.log_object, self.input["dest_mailbox"], self.environment
        )

    def start(self):
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
        self.number_of_chunks = self._get_number_of_chunks()
        self.http_response.raise_for_status()
        self.chunked = (
            self.http_response.status_code == HTTPStatus.PARTIAL_CONTENT.value
        )
        self._get_aws_bucket_and_key()

        if self.http_response.headers.get("Mex-Messagetype") == "REPORT":
            self._handle_report_message()
        elif self.number_of_chunks == 1:
            self._handle_single_chunk_message()
        else:
            self._handle_multiple_chunk_message()

    def _handle_multiple_chunk_message(self):
        self.log_object.write_log(
            "MESHFETCH0013", None, {"message_id": self.message_id}
        )
        if self.current_chunk == 1:
            self._create_multipart_upload()
        self._read_bytes_into_buffer()
        self.log_object.write_log(
            "MESHFETCH0001a",
            None,
            {
                "length": self.http_headers_bytes_read,
                "message_id": self.message_id,
            },
        )
        last_chunk = self._is_last_chunk(self.current_chunk)
        if last_chunk:
            self._finish_multipart_upload()
            self.mailbox.acknowledge_message(self.message_id)
            self.log_object.write_log(
                "MESHFETCH0004", None, {"message_id": self.message_id}
            )
        else:
            self.current_chunk += 1
            self.log_object.write_log(
                "MESHFETCH0003",
                None,
                {"chunk": self.current_chunk, "message_id": self.message_id},
            )
        self._update_response_and_mailbox_cleanup(complete=last_chunk)

    def _handle_single_chunk_message(self):
        self.log_object.write_log(
            "MESHFETCH0011", None, {"message_id": self.message_id}
        )
        chunk_data = self.http_response.raw.read(decode_content=True)
        self._upload_to_s3(chunk_data, s3_key=self.s3_key)
        self.mailbox.acknowledge_message(self.message_id)
        self._update_response_and_mailbox_cleanup(complete=True)
        self.log_object.write_log(
            "MESHFETCH0012", None, {"message_id": self.message_id}
        )

    def _handle_report_message(self):
        self.log_object.write_log(
            "MESHFETCH0010", None, {"message_id": self.message_id}
        )
        buffer = json.dumps(dict(self.http_response.headers)).encode("utf-8")
        self.http_headers_bytes_read = len(buffer)
        self._upload_to_s3(buffer, s3_key=self.s3_key)
        self.mailbox.acknowledge_message(self.message_id)
        self._update_response_and_mailbox_cleanup(complete=True)
        self.log_object.write_log(
             "MESHFETCH0012", None, {"message_id": self.message_id}
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

    def _is_last_chunk(self, chunk_num) -> bool:
        chunk_range = self.http_response.headers.get("Mex-Chunk-Range", "1:1")
        self.number_of_chunks = int(chunk_range.split(":")[1])
        return chunk_num == self.number_of_chunks

    def _get_number_of_chunks(self) -> int:
        chunk_range = self.http_response.headers.get("Mex-Chunk-Range", "1:1")
        number_of_chunks = int(chunk_range.split(":")[1])
        return number_of_chunks

    def _upload_part_to_s3(self, buffer):
        """Upload a part to S3 and check response"""
        overflow_filename = f"part_overflow_{self.message_id}.tmp"
        self.s3_tempfile_key = os.path.basename(self.s3_key) + overflow_filename

        # check if part_overflow_{message_id}.tmp exists and pre-pend to buffer
        try:
            s3_response = self.s3_client.get_object(
                Bucket=self.s3_bucket, Key=self.s3_tempfile_key
            )
            if s3_response["ResponseMetadata"]["HTTPStatusCode"] == HTTPStatus.OK.value:
                pre_buffer = s3_response["Body"].read()
                buffer = pre_buffer + buffer

                self.log_object.write_log(
                    "MESHFETCH0002b",
                    None,
                    {
                        "number_of_chunks": self.number_of_chunks,
                        "aws_part_size": len(pre_buffer),
                        "aws_upload_id": self.aws_upload_id,
                    },
                )

            self.s3_client.delete_object(
                Bucket=self.s3_bucket,
                Key=self.s3_tempfile_key,
                BypassGovernanceRetention=True,
            )
        except ClientError as e:
            self.log_object.write_log(
                "MESHFETCH0002c",
                None,
                {
                    "client_error": e,
                    "number_of_chunks": self.number_of_chunks,
                    "aws_upload_id": self.aws_upload_id,
                },
            )

        try:
            response = self.s3_client.upload_part(
                Body=buffer,
                Bucket=self.s3_bucket,
                Key=self.s3_key,
                PartNumber=self.aws_current_part_id,
                ContentLength=len(buffer),
                UploadId=self.aws_upload_id,
            )
        except ClientError as e:
            self.response.update({"statusCode": HTTPStatus.INTERNAL_SERVER_ERROR.value})
            self.log_object.write_log(
                "MESHFETCH0006",
                None,
                {
                    "key": self.s3_key,
                    "bucket": self.s3_bucket,
                    "content_length": len(buffer),
                    "aws_upload_id": self.aws_upload_id,
                    "error": e,
                },
            )
            raise e

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
                "number_of_chunks": self.number_of_chunks,
                "aws_part_id": self.aws_current_part_id,
                "aws_part_size": len(buffer),
                "aws_upload_id": self.aws_upload_id,
                "etag": etag,
            },
        )
        return etag

    def _upload_to_s3(self, buffer, s3_key):
        self.s3_client.put_object(
            Bucket=self.s3_bucket,
            Key=s3_key,
            Body=buffer,
        )
        self.log_object.write_log(
            "MESHFETCH0002a",
            None,
            {
                "HEADERS": self.http_response.headers,
                "RESPONSE": self.http_response,
                "aws_part_size": len(buffer),
                "aws_upload_id": self.aws_upload_id,
            },
        )

    def _create_multipart_upload(self):
        """Create an S3 multipart upload"""
        try:
            self.log_object.write_log(
                "MESHFETCH0009",
                None,
                {
                    "CHUNKS": self.number_of_chunks,
                    "key": self.s3_key,
                    "bucket": self.s3_bucket,
                },
            )
            multipart_upload = self.s3_client.create_multipart_upload(
                Bucket=self.s3_bucket,
                Key=self.s3_key,
            )
            self.aws_upload_id = multipart_upload["UploadId"]
        except ClientError as e:
            self.response.update({"statusCode": HTTPStatus.INTERNAL_SERVER_ERROR.value})
            self.log_object.write_log(
                "MESHFETCH0005",
                None,
                {
                    "key": self.s3_key,
                    "bucket": self.s3_bucket,
                    "error": e,
                },
            )
            raise e

    def _finish_multipart_upload(self):
        """Complete the s3 multipart upload"""
        try:
            self.log_object.write_log(
                "MESHFETCH0008",
                None,
                {
                    "mesh_msg_id": self.message_id,
                    "key": self.s3_key,
                    "bucket": self.s3_bucket,
                    "aws_upload_id": self.aws_upload_id,
                    "PARTS": {"Parts": self.aws_part_etags},
                },
            )

            self.s3_client.complete_multipart_upload(
                Bucket=self.s3_bucket,
                Key=self.s3_key,
                UploadId=self.aws_upload_id,
                MultipartUpload={"Parts": self.aws_part_etags},
            )

        except ClientError as e:
            self.response.update({"statusCode": HTTPStatus.INTERNAL_SERVER_ERROR.value})
            self.log_object.write_log(
                "MESHFETCH0007",
                None,
                {
                    "number_of_chunks": self.number_of_chunks,
                    "mesh_msg_id": self.message_id,
                    "key": self.s3_key,
                    "bucket": self.s3_bucket,
                    "aws_upload_id": self.aws_upload_id,
                    "error": e,
                },
            )
            raise e

    def _update_response_and_mailbox_cleanup(self, complete: bool):
        self.response.update({"statusCode": self.http_response.status_code})
        self.response["body"].update(
            {
                "complete": complete,
                "chunk_num": self.current_chunk,
                "aws_upload_id": self.aws_upload_id,
                "aws_current_part_id": self.aws_current_part_id,
                "aws_part_etags": self.aws_part_etags,
                "internal_id": self.internal_id,
                "file_name": self._get_filename(),
            }
        )
        self.mailbox.clean_up()

    def _read_bytes_into_buffer(self):
        part_buffer = b""
        for buffer in self.http_response.iter_content(
            chunk_size=self.DEFAULT_BUFFER_SIZE
        ):
            self.log_object.write_log(
                "MESHFETCH0003a", None, {"buffer_len": len(buffer)}
            )
            # Condition here to account for odd sized chunks
            if len(buffer) < 5 * self.MEBIBYTE:
                self._upload_to_s3(buffer, self.s3_tempfile_key)
            else:
                self._upload_part_to_s3(part_buffer + buffer)
                self.http_headers_bytes_read += len(buffer)


# create instance of class in global space
# this ensures initial setup of logging/config is only done on cold start
app = MeshFetchMessageChunkApplication()


def lambda_handler(event, context):
    """Standard lambda_handler"""
    return app.main(event, context)
