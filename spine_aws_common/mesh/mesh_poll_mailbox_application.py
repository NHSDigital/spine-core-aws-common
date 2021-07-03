"""
Module for MESH API functionality for step functions
"""
import json
from spine_aws_common import LambdaApplication


class MeshPollMailboxApplication(LambdaApplication):
    """
    MESH API Lambda for sending a message
    """

    def __init__(self, additional_log_config=None, load_ssm_params=False):
        """
        Init variables
        """
        super().__init__(additional_log_config, load_ssm_params)
        self.mailbox = None

    def initialise(self):
        # initialise
        self.mailbox = self.event['mailbox']

    def start(self):
        # do actual work
        print("Calling start on my module")
        # to set response for the lambda
        self.response = {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": {
                "messageCount": 1,
                "messageList": [
                    {"messageId": "12345", "mailbox": self.mailbox}
                ]
            }
        }
        print(json.dumps(self.response))


# create instance of class in global space
# this ensures initial setup of logging/config is only done on cold start
app = MeshPollMailboxApplication()


def lambda_handler(event, context):
    """
    Standard lambda_handler
    """
    return app.main(event, context)
