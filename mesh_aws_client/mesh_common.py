"""Common methods and classes used for mesh client"""
from collections import namedtuple
from http import HTTPStatus
import atexit
import json
import os
import tempfile

from mesh_client import MeshClient
from urllib3.exceptions import InsecureRequestWarning
import boto3
import requests

from spine_aws_common.logger import Logger


class SingletonCheckFailure(Exception):
    """Singleton check failed"""

    def __init__(self, msg=None):
        super().__init__()
        self.msg = msg


class AwsFailedToPerformError(Exception):
    """Errors raised by AWS functions"""

    def __init__(self, msg=None):
        super().__init__()
        self.msg = msg


class MeshCommon:
    """Common"""

    MIB = 1024 * 1024
    DEFAULT_CHUNK_SIZE = 20 * MIB

    @staticmethod
    def singleton_check(mailbox, my_step_function_name):
        """Find out whether there is another step function running for my mailbox"""
        sfn_client = boto3.client("stepfunctions", region_name="eu-west-2")
        response = sfn_client.list_state_machines()
        # Get my step function arn
        my_step_function_arn = None
        for step_function in response.get("stateMachines", []):
            if step_function.get("name", "") == my_step_function_name:
                my_step_function_arn = step_function.get("stateMachineArn", None)

        # TODO add this check to tests
        if not my_step_function_arn:
            raise SingletonCheckFailure(
                "No executing step function arn for "
                + f"step_function={my_step_function_name}"
            )

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

    @staticmethod
    def convert_params_to_dict(params):
        """Convert paramater dict to key:value dict"""
        new_dict = {}
        for entry in params:
            name = entry.get("Name", None)
            if name:
                var_name = os.path.basename(name)
                new_dict[var_name] = entry.get("Value", None)
        return new_dict

    @staticmethod
    def return_failure(log_object, status, logpoint, mailbox, message=""):
        """Return a failure response with retry"""
        log_object.write_log(logpoint, None, {"mailbox": mailbox, "error": message})
        return {
            "statusCode": status,
            "headers": {
                "Content-Type": "application/json",
                "Retry-After": 18000,
            },
            "body": {
                "internal_id": log_object.internal_id,
                "error": message,
            },
        }

    @staticmethod
    def get_ssm_params(path, recursive=False, decryption=True):
        """Get parameters from SSM param store and return as simple dict"""
        # TODO region name fix
        ssm_client = boto3.client("ssm", region_name="eu-west-2")

        params_result = ssm_client.get_parameters_by_path(
            Path=path,
            Recursive=recursive,
            WithDecryption=decryption,
        )
        params = params_result.get("Parameters", {})
        new_params_dict = {}
        for entry in params:
            name = entry.get("Name", None)
            if name:
                var_name = os.path.basename(name)
                new_params_dict[var_name] = entry.get("Value", None)
        return new_params_dict


class ExtendedMeshClient(MeshClient):
    """Extended functionality for lambda send"""


# Named tuple for holding Mesh Message info
MeshMessage = namedtuple(
    "MeshMessage",
    [
        "filename",
        "body",
        "src_mailbox",
        "dest_mailbox",
        "workflow_id",
        "message_id",
    ],
)


class MeshMailbox:  # pylint: disable=too-many-instance-attributes
    """
    Mesh mailbox object, gets parameters from SSM Parameter Store
    DEPRECATED Version
    """

    VERSION = "0.0.1"

    def __init__(self, log_object: Logger, mailbox, environment="default"):
        self.mailbox = mailbox
        self.common_params = None
        self.mailbox_params = None
        self.ca_cert_file = None
        self.client_cert_file = None
        self.client_key_file = None
        self.environment = environment
        self.dest_mailbox = None
        self.workflow_id = None
        self.temp_dir_object = None
        self.log_object = log_object
        self._setup()
        atexit.register(self.clean_up)

    def clean_up(self):
        """Close mesh client at exit"""
        self.mesh_client.close()

    def _setup(self):
        """Get the parameters from SSM paramter store"""
        # TODO refactor
        ssm_client = boto3.client("ssm", region_name="eu-west-2")
        self.log_object.write_log(
            "MESH0001", None, {"mailbox": self.mailbox, "environment": self.environment}
        )
        common_params_result = ssm_client.get_parameters_by_path(
            Path=f"/{self.environment}/mesh", Recursive=False, WithDecryption=True
        )
        self.common_params = MeshCommon.convert_params_to_dict(
            common_params_result.get("Parameters", {})
        )
        mailbox_params_result = ssm_client.get_parameters_by_path(
            Path=f"/{self.environment}/mesh/mailboxes/{self.mailbox}",
            Recursive=False,
            WithDecryption=True,
        )
        self.mailbox_params = MeshCommon.convert_params_to_dict(
            mailbox_params_result.get("Parameters", {})
        )
        self._write_certs_to_files()

        maybe_verify = bool(self.common_params.get("MESH_VERIFY_SSL") == "True")

        if not maybe_verify:
            requests.urllib3.disable_warnings(InsecureRequestWarning)
        self.mesh_client = ExtendedMeshClient(
            self.common_params["MESH_URL"],
            self.mailbox,
            self.mailbox_params["MAILBOX_PASSWORD"],
            shared_key=self.common_params["MESH_SHARED_KEY"].encode("utf8"),
            cert=(self.client_cert_file.name, self.client_key_file.name),
            verify=self.ca_cert_file.name if maybe_verify else None,
            max_chunk_size=MeshCommon.DEFAULT_CHUNK_SIZE,
        )

    def _write_certs_to_files(self):
        """Write the certificates to a local file"""
        # pylint: disable=consider-using-with
        self.temp_dir_object = tempfile.TemporaryDirectory()
        temp_dir = self.temp_dir_object.name

        # store as temporary files for the mesh client
        self.client_cert_file = tempfile.NamedTemporaryFile(dir=temp_dir, delete=False)
        client_cert = self.common_params["MESH_CLIENT_CERT"]
        self.client_cert_file.write(client_cert.encode("utf-8"))
        self.client_cert_file.seek(0)

        self.client_key_file = tempfile.NamedTemporaryFile(dir=temp_dir, delete=False)
        client_key = self.common_params["MESH_CLIENT_KEY"]
        self.client_key_file.write(client_key.encode("utf-8"))
        self.client_key_file.seek(0)

        self.ca_cert_file = None
        if self.common_params.get("MESH_VERIFY_SSL", False) == "True":
            self.ca_cert_file = tempfile.NamedTemporaryFile(dir=temp_dir, delete=False)
            ca_cert = self.common_params["MESH_CA_CERT"]
            self.ca_cert_file.write(ca_cert.encode("utf-8"))
            self.ca_cert_file.seek(0)
        # pylint: enable=consider-using-with

    def set_destination_and_workflow(self, dest_mailbox, workflow_id):
        """Set destination mailbox and workflow_id"""
        self.dest_mailbox = dest_mailbox
        self.workflow_id = workflow_id

    def authenticate(self):
        """Authenticate to MESH mailbox"""
        return self.mesh_client.handshake()

    def send_chunk(
        self,
        mesh_message_object,
        chunk=False,
        chunk_size=MeshCommon.DEFAULT_CHUNK_SIZE,
        chunk_num=1,
    ):
        """Send a chunk"""
        # override mailbox dest_mailbox if provided in message_object
        if mesh_message_object.dest_mailbox:
            dest_mailbox = mesh_message_object.dest_mailbox
        else:
            dest_mailbox = self.mailbox
        # override mailbox workflow_id if provided in message_object
        if mesh_message_object.workflow_id:
            workflow_id = mesh_message_object.workflow_id
        else:
            workflow_id = self.mailbox.workflow_id
        if not chunk:
            message_id = self.mesh_client.send_message(
                dest_mailbox,
                workflow_id=workflow_id,
                filename=mesh_message_object.filename,
                data=mesh_message_object.body,
            )
            mesh_message_object = mesh_message_object._replace(message_id=message_id)

        else:
            # TODO chunking is more interesting, as mesh_client doesn't have a
            # function for sending one chunk only
            offset = chunk_size * chunk_num
            print(f"Calculated offset is {offset}")
            print("CHUNKING ON SEND IS NOT IMPLEMENTED YET")
            return (HTTPStatus.NOT_IMPLEMENTED.value, None)
        return (HTTPStatus.OK.value, mesh_message_object)

    def get_chunk(
        self,
        message_id,
        chunk=False,
        chunk_size=MeshCommon.DEFAULT_CHUNK_SIZE,
        chunk_num=1,
    ):
        """Get a chunk"""
        if not chunk:
            message_object = self.mesh_client.retrieve_message(message_id)
            # for (header, value) in message_object.mex_headers():
            #     print(f"{header}={value}")
            filename = message_object.mex_header("filename")
            if not filename:
                filename = message_id
            workflow_id = message_object.mex_header(
                "workflowid", default="Not Provided"
            )
            src_mailbox = message_object.mex_header("from", default="Not Provided")
            # TODO get other info available - compression etc
            return_message_object = MeshMessage(
                filename=filename,
                message_id=message_id,
                body=message_object.read(),
                dest_mailbox=self.mailbox,
                src_mailbox=src_mailbox,
                workflow_id=workflow_id,
            )
            return (HTTPStatus.OK.value, return_message_object)

        # chunked
        offset = chunk_size * chunk_num
        print(f"Calculated offset is {offset}")
        print("CHUNKING ON RECEIVE IS NOT IMPLEMENTED YET")
        return (HTTPStatus.NOT_IMPLEMENTED.value, None)
