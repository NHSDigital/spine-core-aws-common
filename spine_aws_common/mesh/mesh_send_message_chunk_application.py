"""
Module for MESH API functionality for step functions
"""
import os
from http import HTTPStatus
import boto3
from spine_aws_common import LambdaApplication
from spine_aws_common.mesh.mesh_common import MeshCommon, MeshMailbox


class MeshSendMessageChunkApplication(LambdaApplication):
    """
    MESH API Lambda for sending a message / message chunk
    """

    def __init__(self, additional_log_config=None, load_ssm_params=False):
        """
        Init variables
        """
        super().__init__(additional_log_config, load_ssm_params)
        self.mailbox = None
        self.input = {}
        self.body = None
        self.environment = os.environ.get("ENV", "default")

    def start(self):
        # TODO refactor
        # TODO add log points
        self.input = self.event.get("body", {})
        self.response = self.event

        is_finished = self.input.get("complete", False)
        if is_finished:
            # TODO log error
            self.response.update({"statusCode": HTTPStatus.INTERNAL_SERVER_ERROR.value})
            raise SystemError("Already completed upload to MESH")

        total_chunks = self.input.get("total_chunks", 1)
        current_chunk = self.input.get("chunk_number", 1)
        chunk_size = self.input.get("chunk_size", MeshCommon.DEFAULT_CHUNK_SIZE)
        chunked = self.input.get("chunked", False)
        message_id = self.input.get("message_id", None)

        self.mailbox = MeshMailbox(self.input["src_mailbox"], self.environment)
        self.mailbox.set_destination_and_workflow(
            self.input["dest_mailbox"], self.input["workflow_id"]
        )
        bucket = self.input["bucket"]
        key = self.input["key"]

        file_contents = self._get_file_from_s3(
            bucket,
            key,
            chunked=chunked,
            current_chunk=current_chunk,
            chunk_size=chunk_size,
        )
        print(f"Got file contents:>{file_contents}<")
        self.body = file_contents
        if file_contents:
            (status_code, message_id) = self.mailbox.send_chunk(
                message_id,
                chunk_size=chunk_size,
                chunk_num=current_chunk,
                data=file_contents,
            )
            status_code = HTTPStatus.OK.value
        else:
            status_code = HTTPStatus.NOT_FOUND.value
            self.response.update({"statusCode": status_code})
            raise FileNotFoundError

        is_finished = current_chunk >= total_chunks if chunked else True
        if chunked and not is_finished:
            current_chunk += 1

        # update input event to send as response
        self.response.update({"statusCode": status_code})
        self.response["body"].update(
            {
                "complete": is_finished,
                "message_id": message_id,
                "chunk_number": current_chunk,
            }
        )

    @staticmethod
    def _get_file_from_s3(
        bucket,
        key,
        chunked=False,
        current_chunk=1,
        chunk_size=MeshCommon.DEFAULT_CHUNK_SIZE,
    ):
        """Get a file or chunk of a file from S3"""
        file_content = None
        s3_client = boto3.client("s3")
        if not chunked:
            # Read whole file
            response = s3_client.get_object(Bucket=bucket, Key=key)
        else:
            # Read a chunk from file
            start = current_chunk * chunk_size
            end = (current_chunk + 1) * chunk_size - 1
            range_spec = f"bytes={start}-{end}"
            response = s3_client.get_object(
                Bucket=bucket, Key=key, Range=range_spec, PartNumber=current_chunk
            )
            # TODO sanity check number of parts etc
        body = response.get("Body", None)
        if body:
            # TODO streaming (this reads whole file into memory)
            file_content = body.read()
            if len(file_content) == 0:
                file_content = None
        else:
            file_content = None
        return file_content


# create instance of class in global space
# this ensures initial setup of logging/config is only done on cold start
app = MeshSendMessageChunkApplication()


def lambda_handler(event, context):
    """
    Standard lambda_handler
    """
    return app.main(event, context)
