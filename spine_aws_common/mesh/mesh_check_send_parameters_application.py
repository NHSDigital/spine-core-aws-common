"""
Module for MESH API functionality for step functions
"""
import json
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
        self.environment = self.system_config.get("ENV", "default")
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
        self.my_step_function_name = f"{self.environment}-mesh-send-message"

    def start(self):
        # TODO nicer failure, log error and parameters missing in request
        bucket = self.event.detail["requestParameters"]["bucketName"]
        key = self.event.detail["requestParameters"]["key"]

        self.log_object.write_log("MESHSEND0001", None, {"bucket": bucket, "file": key})

        # TODO nicer failure, log error and parameters missing in SSM Parameter Store
        (src_mailbox, dest_mailbox, workflow_id) = self._get_mapping(bucket)

        self.log_object.write_log("MESHSEND0002", None, {"mailbox": src_mailbox})
        try:
            self._singleton_check_ok(src_mailbox)
        except SingletonCheckFailure as e:
            self._return_failure(500, src_mailbox, message=e.msg)
            return

        file_size = self._get_file_size(bucket, key)
        (do_chunking, chunks) = calculate_chunks(file_size, self.chunk_size)
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
            "statusCode": 200,
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
            "headers": {"Content-Type": "application/json"},
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

    def _get_mapping(self, bucket):
        """Get bucket to mailbox mapping from SSM parameter store"""
        config = parameters.get_parameters(
            f"/{self.environment}/mesh/mapping/{bucket}/"
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

    def _singleton_check_ok(self, mailbox):
        """Find out whether there is another step function running for my mailbox"""
        sfn_client = boto3.client("stepfunctions")
        response = sfn_client.list_state_machines()
        # Get my step function arn
        my_step_function_arn = None
        for step_function in response.get("stateMachines", []):
            if step_function.get("name", "") == self.my_step_function_name:
                my_step_function_arn = step_function.get("stateMachineArn", None)

        if not my_step_function_arn:
            raise SingletonCheckFailure("Could not retrieve step function arn")

        response = sfn_client.list_executions(
            stateMachineArn=my_step_function_arn,
            statusFilter="RUNNING",
        )
        currently_running_step_funcs = []
        for execution in response["executions"]:
            currently_running_step_funcs.append(execution["executionArn"])

        exec_count = 0
        for execution_arn in currently_running_step_funcs:
            response = sfn_client.describe_execution(executionArn=execution_arn)
            step_function_input = json.loads(response.get("input", "{}"))
            input_mailbox = step_function_input.get("mailbox", None)
            if input_mailbox == mailbox:
                exec_count = exec_count + 1
            if exec_count > 1:
                raise SingletonCheckFailure("Process already running for this mailbox")

        return True


# create instance of class in global space
# this ensures initial setup of logging/config is only done on cold start
app = MeshCheckSendParametersApplication(additional_log_config="mesh_application.cfg")


def lambda_handler(event, context):
    """Standard lambda_handler"""
    return app.main(event, context)
