"""
Module for MESH API functionality for step functions
"""
import json
import gzip
from http import HTTPStatus
import os

import boto3

from spine_aws_common import LambdaApplication
from mesh_aws_client.mesh_mailbox import MeshMailbox, MeshMessage
from mesh_aws_client.mesh_common import MeshCommon


class MeshSendMessageChunkApplication(
    LambdaApplication
):  # pylint: disable=too-many-instance-attributes
    """
    MESH API Lambda for sending a message / message chunk
    """

    MEBIBYTE = 1024 * 1024
    DEFAULT_BUFFER_SIZE = 20 * MEBIBYTE

    def __init__(self, additional_log_config=None, load_ssm_params=False):
        """
        Init variables
        """
        super().__init__(additional_log_config, load_ssm_params)
        self.mailbox = None
        self.input = {}
        self.body = None
        self.environment = os.environ.get("Environment", "default")
        self.chunked = False
        self.current_byte = 0
        self.current_chunk = 1
        self.chunk_size = 0
        self.compression_ratio = 1
        self.will_compress = False
        self.s3_client = None
        self.bucket = ""
        self.key = ""
        self.buffer_size = self.DEFAULT_BUFFER_SIZE
        self.file_size = 0

    def initialise(self):
        """Setup class variables"""
        self.input = self.event.get("body")
        self.response = self.event.raw_event
        self.current_byte = self.input.get("current_byte_position", 0)
        self.current_chunk = self.input.get("chunk_number", 1)
        self.chunk_size = self.input.get("chunk_size", MeshCommon.DEFAULT_CHUNK_SIZE)
        self.chunked = self.input.get("chunked", False)
        self.compression_ratio = self.input.get("compress_ratio", 1)
        self.will_compress = self.input.get("will_compress", False)
        self.s3_client = boto3.client("s3")
        self.bucket = self.input["bucket"]
        self.key = self.input["key"]
        return super().initialise()

    def _get_file_from_s3(self):
        """Get a file or chunk of a file from S3"""
        start_byte = self.current_byte
        end_byte = start_byte + (self.chunk_size * self.compression_ratio)
        if end_byte > self.file_size:
            end_byte = self.file_size
        while self.current_byte < end_byte:
            bytes_to_end = end_byte - self.current_byte
            if bytes_to_end > self.buffer_size:
                range_spec = (
                    f"bytes={self.current_byte}-"
                    + f"{self.current_byte + self.buffer_size - 1}"
                )
                self.current_byte = self.current_byte + self.buffer_size
            else:
                range_spec = f"bytes={self.current_byte}-{end_byte-1}"
                self.current_byte = end_byte

            response = self.s3_client.get_object(
                Bucket=self.bucket, Key=self.key, Range=range_spec
            )

            body = response.get("Body", None)
            if body:
                file_content = body.read()
                if len(file_content) == 0:
                    file_content = None
                self.log_object.write_log(
                    "MESHSEND0006",
                    None,
                    {
                        "file": self.key,
                        "bucket": self.bucket,
                        "num_bytes": len(file_content),
                        "byte_range": range_spec,
                    },
                )
            else:
                file_content = None

            if self.will_compress:
                compressed_bytes = gzip.compress(file_content)
                yield compressed_bytes
            else:
                yield file_content

    def start(self):
        """Main body of lambda"""

        is_finished = self.input.get("complete", False)
        if is_finished:
            self.response.update({"statusCode": HTTPStatus.INTERNAL_SERVER_ERROR.value})
            raise SystemError("Already completed upload to MESH")

        total_chunks = self.input.get("total_chunks", 1)
        message_id = self.input.get("message_id", None)

        file_response = self.s3_client.head_object(Bucket=self.bucket, Key=self.key)
        self.file_size = file_response["ContentLength"]
        self.log_object.write_log(
            "MESHSEND0005",
            None,
            {
                "file": self.key,
                "bucket": self.bucket,
                "chunk_num": self.current_chunk,
                "max_chunk": total_chunks,
            },
        )

        self.mailbox = MeshMailbox(
            self.log_object, self.input["src_mailbox"], self.environment
        )
        self.mailbox.set_destination_and_workflow(
            self.input["dest_mailbox"], self.input["workflow_id"]
        )

        message_object = MeshMessage(
            file_name=os.path.basename(self.key),
            data=self._get_file_from_s3(),
            message_id=message_id,
            dest_mailbox=self.mailbox.dest_mailbox,
            src_mailbox=self.mailbox.mailbox,
            workflow_id=self.mailbox.workflow_id,
            will_compress=self.will_compress,
        )
        if self.file_size > 0:
            response = self.mailbox.send_chunk(
                mesh_message_object=message_object,
                number_of_chunks=total_chunks,
                chunk_num=self.current_chunk,
            )
            status_code = response.status_code
            message_id = json.loads(response.text)["messageID"]
            status_code = HTTPStatus.OK.value
        else:
            status_code = HTTPStatus.NOT_FOUND.value
            self.response.update({"statusCode": status_code})
            raise FileNotFoundError

        is_finished = self.current_chunk >= total_chunks if self.chunked else True
        if self.chunked and not is_finished:
            self.current_chunk += 1

        if is_finished:
            # check mailbox for any reports
            _response, _messages = self.mailbox.list_messages()

        # update input event to send as response
        self.response.update({"statusCode": status_code})
        self.response["body"].update(
            {
                "complete": is_finished,
                "message_id": message_id,
                "chunk_number": self.current_chunk,
                "current_byte_position": self.current_byte,
            }
        )

        self.mailbox.clean_up()


# create instance of class in global space
# this ensures initial setup of logging/config is only done on cold start
app = MeshSendMessageChunkApplication()


def lambda_handler(event, context):
    """Standard lambda_handler"""
    return app.main(event, context)
