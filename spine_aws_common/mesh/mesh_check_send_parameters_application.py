"""
Module for MESH API functionality for step functions
"""
from http import HTTPStatus
import os
from math import ceil
import boto3
from aws_lambda_powertools.utilities import parameters
from aws_lambda_powertools.utilities.data_classes import EventBridgeEvent
from spine_aws_common import LambdaApplication
from spine_aws_common.utilities import human_readable_bytes
from spine_aws_common.mesh.mesh_common import MeshCommon, SingletonCheckFailure


def calculate_chunks(file_size, chunk_size):
    """Helper for number of chunks"""
    chunks = ceil(file_size / chunk_size)
    do_chunking = chunks > 1
    return (do_chunking, chunks)


class MeshCheckSendParametersApplication(LambdaApplication):
    """MESH API Lambda for sending a message"""

    def __init__(self, additional_log_config=None, load_ssm_params=False):
        """Initialise variables"""
        super().__init__(additional_log_config, load_ssm_params)
        self.environment = self.system_config.get("Environment", "default")
        self.chunk_size = None
        self.my_step_function_name = None

    def _get_internal_id(self):
        """Override to stop crashing when getting from non-dict event"""
        return self._create_new_internal_id()

    def process_event(self, event):
        return EventBridgeEvent(event)

    def initialise(self):
        self.chunk_size = int(
            self.system_config.get("CHUNK_SIZE", MeshCommon.DEFAULT_CHUNK_SIZE)
        )
        # TODO figure out better way to do this:
        self.my_step_function_name = f"{self.environment}-send-message"

    def start(self):
        # in case of crash, set to internal server error so next stage fails
        self.response = {"statusCode": HTTPStatus.INTERNAL_SERVER_ERROR.value}
        # TODO nicer failure, log error and parameters missing in request
        bucket = self.event.detail["requestParameters"]["bucketName"]
        key = self.event.detail["requestParameters"]["key"]

        self.log_object.write_log("MESHSEND0001", None, {"bucket": bucket, "file": key})

        # TODO nicer failure, log error and parameters missing in SSM Parameter Store
        (src_mailbox, dest_mailbox, workflow_id) = self._get_mapping(bucket, key)

        self.log_object.write_log("MESHSEND0002", None, {"mailbox": src_mailbox})
        try:
            MeshCommon.singleton_check(src_mailbox, self.my_step_function_name)
        except SingletonCheckFailure as e:
            self._return_failure(
                HTTPStatus.TOO_MANY_REQUESTS.value, src_mailbox, message=e.msg
            )
            return

        file_size = self._get_file_size(bucket, key)
        (do_chunking, chunks) = calculate_chunks(file_size, self.chunk_size)
        # TODO compression calculations and recaculate chunks and chunk_size

        self.log_object.write_log(
            "MESHSEND0004",
            None,
            {
                "src_mailbox": src_mailbox,
                "dest_mailbox": dest_mailbox,
                "workflow_id": workflow_id,
                "bucket": bucket,
                "file": key,
                "file_size": human_readable_bytes(file_size),
                "chunks": chunks,
                "chunk_size": human_readable_bytes(self.chunk_size),
            },
        )
        self.response = {
            "statusCode": HTTPStatus.OK.value,
            "headers": {"Content-Type": "application/json"},
            "body": {
                "internal_id": self.log_object.internal_id,
                "src_mailbox": src_mailbox,
                "dest_mailbox": dest_mailbox,
                "workflow_id": workflow_id,
                "bucket": bucket,
                "key": key,
                "chunk": do_chunking,
                "chunk_number": 1,
                "total_chunks": chunks,
                "chunk_size": self.chunk_size,
                "complete": False,
                "message_id": None,
            },
        }

    def _return_failure(self, status, mailbox, message=""):
        self.response = {
            "statusCode": status,
            "headers": {
                "Content-Type": "application/json",
                "Retry-After": 18000,
            },
            "body": {
                "internal_id": self.log_object.internal_id,
                "error": message,
            },
        }
        self.log_object.write_log(
            "MESHSEND0003",
            None,
            {"mailbox": mailbox, "error": message},
        )

    def _get_mapping(self, bucket, key):
        """Get bucket to mailbox mapping from SSM parameter store"""
        folder = os.path.dirname(key)
        if len(folder) > 0:
            folder += "/"

        config = parameters.get_parameters(
            f"/{self.environment}/mesh/mapping/{bucket}/{folder}"
        )
        src_mailbox = config["src_mailbox"]
        dest_mailbox = config["dest_mailbox"]
        workflow_id = config["workflow_id"]
        return (src_mailbox, dest_mailbox, workflow_id)

    @staticmethod
    def _get_file_size(bucket, key):
        """Get file size"""
        s3_client = boto3.client("s3")
        response = s3_client.head_object(Bucket=bucket, Key=key)
        file_size = response.get("ContentLength")
        return file_size
