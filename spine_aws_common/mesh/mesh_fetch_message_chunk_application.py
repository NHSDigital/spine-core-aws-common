"""
Module for MESH API functionality for step functions
"""
from spine_aws_common import LambdaApplication


class MeshFetchMessageChunkApplication(LambdaApplication):
    """
    MESH API Lambda for sending a message
    """

    def __init__(self, additional_log_config=None, load_ssm_params=False):
        """
        Init variables
        """
        super().__init__(additional_log_config, load_ssm_params)
        self.mailbox = None

    def start(self):
        # do actual work
        # to set response for the lambda
        self.response = '{"isLastChunk":true}'


# create instance of class in global space
# this ensures initial setup of logging/config is only done on cold start
app = MeshFetchMessageChunkApplication(additional_log_config='mesh_application.cfg')


def lambda_handler(event, context):
    """
    Standard lambda_handler
    """
    return app.main(event, context)
