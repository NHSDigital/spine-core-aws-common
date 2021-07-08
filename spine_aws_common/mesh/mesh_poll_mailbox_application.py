"""
Module for MESH API functionality for step functions
"""
import os
from http import HTTPStatus
from spine_aws_common import LambdaApplication
from spine_aws_common.mesh.mesh_common import MeshMailbox
from spine_aws_common.mesh.mesh_common import MeshCommon, SingletonCheckFailure


class MeshPollMailboxApplication(LambdaApplication):
    """
    MESH API Lambda for sending a message
    """

    def __init__(self, additional_log_config=None, load_ssm_params=False):
        """
        Init variables
        """
        super().__init__(additional_log_config, load_ssm_params)
        self.mailbox_name = None
        self.environment = os.environ.get("Environment", "default")
        # TODO figure out better way to do this:
        self.my_step_function_name = f"{self.environment}-mesh-get-messages"

    def initialise(self):
        # initialise
        self.mailbox_name = self.event["mailbox"]

    def start(self):
        # in case of crash
        self.response = {"statusCode": HTTPStatus.INTERNAL_SERVER_ERROR.value}
        mailbox = MeshMailbox(self.log_object, self.mailbox_name, self.environment)

        try:
            MeshCommon.singleton_check(self.mailbox_name, self.my_step_function_name)
        except SingletonCheckFailure as e:
            self._return_failure(
                HTTPStatus.TOO_MANY_REQUESTS.value, self.mailbox_name, message=e.msg
            )
            return

        message_list = mailbox.mesh_client.list_messages()
        message_count = len(message_list)
        output_list = []
        if message_count == 0:
            # return 204 to keep state transitions to minimum if no messages
            self.response = {"statusCode": HTTPStatus.NO_CONTENT.value, "body": {}}
            return
        for message in message_list:
            output_list.append(
                {
                    "headers": {"Content-Type": "application/json"},
                    "body": {
                        "complete": False,
                        "internal_id": self.log_object.internal_id,
                        "message_id": message,
                        "dest_mailbox": self.mailbox_name,
                    },
                }
            )

        # to set response for the lambda
        self.response = {
            "statusCode": HTTPStatus.OK.value,
            "headers": {"Content-Type": "application/json"},
            "body": {
                "internal_id": self.log_object.internal_id,
                "message_count": message_count,
                "message_list": output_list,
            },
        }
        print(self.response)

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
            "MESHPOLL0003", None, {"mailbox": mailbox, "error": message}
        )
