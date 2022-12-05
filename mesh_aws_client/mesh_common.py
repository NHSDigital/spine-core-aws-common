"""Common methods and classes used for mesh client"""
from collections import namedtuple
import os
import json
import boto3

REGION_NAME = os.environ.get("AWS_REGION", "eu-west-2")


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
    def get_params(path, recursive=False, decryption=True):
        """
        Get parameters from SSM and secrets manager
        """
        ssm_client = boto3.client("ssm", region_name=REGION_NAME)
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
        if os.environ.get("use_secrets_manager") == "true":
            secrets_client = boto3.client("secretsmanager", region_name=REGION_NAME)
            all_secrets_dict = secrets_client.list_secrets()
            all_secrets_list = all_secrets_dict["SecretList"]
            for secret in all_secrets_list:
                name = secret["Name"]
                if name.startswith(path):
                    secret_value = secrets_client.get_secret_value(SecretId=name)[
                        "SecretString"
                    ]
                    var_name = os.path.basename(name)
                    new_params_dict[var_name] = secret_value
        return new_params_dict


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
