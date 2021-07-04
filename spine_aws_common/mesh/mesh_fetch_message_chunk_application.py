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
        # TODO copy more stuff from send_message_chunk
        # aws_upload_id = self.input.get("aws_upload_id", None)

        # do actual work
        # to set response for the lambda
        # is_finished = current_chunk >= total_chunks if chunked else True
        # s3_client = boto3.client("s3")
        # if chunked:
        #     current_chunk += 1
        #     if is_finished:
        #         s3_client.complete_multipart_upload(
        #             Bucket=bucket, Key=key, UploadId=aws_upload_id
        #         )
        # ...
        # # update input event to send as response
        # self.response.update({"statusCode": status_code})
        # self.response["body"].update(
        #     {
        #         "complete": is_finished,
        #         "message_id": message_id,
        #         "chunk_num": current_chunk,
        #         "aws_upload_id": aws_upload_id,
        #     }
        # )

        self.response = {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": {"complete": True},
        }


# create instance of class in global space
# this ensures initial setup of logging/config is only done on cold start
app = MeshFetchMessageChunkApplication()


def lambda_handler(event, context):
    """
    Standard lambda_handler
    """
    return app.main(event, context)
