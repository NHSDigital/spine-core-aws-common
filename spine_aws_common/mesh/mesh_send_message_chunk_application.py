"""
Module for MESH API functionality for step functions
"""
from spine_aws_common import LambdaApplication


class MeshSendMessageChunkApplication(LambdaApplication):
    """
    MESH API Lambda for sending a message
    """

    def __init__(self, additional_log_config=None, load_ssm_params=False):
        """
        Init variables
        """
        super().__init__(additional_log_config, load_ssm_params)
        self.mailbox = None
        self.input = {}

    def start(self):
        self.input = self.event.get("body", {})
        if self.input.get("complete"):
            # TODO log error
            self.response = {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": self.input,
            }
            return
        #
        # to set response for the lambda
        self.response = {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": self.input,
        }


# create instance of class in global space
# this ensures initial setup of logging/config is only done on cold start
app = MeshSendMessageChunkApplication()


def lambda_handler(event, context):
    """
    Standard lambda_handler
    """
    return app.main(event, context)
